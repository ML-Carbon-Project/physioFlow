from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import streamlit as st

from src.config.settings import (
    AUTH_VALIDATION_TTL_SECONDS,
    SESSION_AUTH_ACCESS_TOKEN_KEY,
    SESSION_AUTH_REFRESH_TOKEN_KEY,
    SESSION_AUTH_USER_KEY,
    SESSION_AUTH_VALIDATED_AT_KEY,
)
from src.i18n import t

# Margem (em segundos) antes da expiracao para tentar renovar o token proativamente.
_TOKEN_REFRESH_MARGIN_SECONDS = 120


@dataclass(frozen=True)
class SupabaseAuthConfig:
    enabled: bool
    url: str | None
    client_key: str | None
    admin_emails: tuple[str, ...]
    allow_signup: bool


def _secret_get(key: str, default: Any = None) -> Any:
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


def _secret_section(name: str) -> dict[str, Any]:
    try:
        if name in st.secrets:
            return dict(st.secrets[name])
    except Exception:
        return {}
    return {}


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def get_auth_config() -> SupabaseAuthConfig:
    section = _secret_section("supabase")
    url = section.get("url") or _secret_get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    client_key = (
        section.get("publishable_key")
        or section.get("anon_key")
        or _secret_get("SUPABASE_PUBLISHABLE_KEY")
        or os.getenv("SUPABASE_PUBLISHABLE_KEY")
        or _secret_get("SUPABASE_ANON_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )
    admin_emails_raw = section.get("admin_emails", [])
    admin_emails = tuple(str(email).strip().lower() for email in admin_emails_raw if str(email).strip())
    enabled_value = section.get("enabled")
    enabled = _to_bool(enabled_value) if enabled_value is not None else bool(url and client_key)
    allow_signup_value = section.get("allow_signup")
    allow_signup = _to_bool(allow_signup_value) if allow_signup_value is not None else True
    return SupabaseAuthConfig(enabled=enabled, url=url, client_key=client_key, admin_emails=admin_emails, allow_signup=allow_signup)


def is_auth_enabled() -> bool:
    return get_auth_config().enabled


def _create_supabase_client():
    config = get_auth_config()
    if not config.enabled:
        return None
    if not config.url or not config.client_key:
        raise RuntimeError(t("auth.error.missing_credentials_env"))
    try:
        from supabase import create_client
    except ImportError as exc:
        raise RuntimeError(t("auth.error.supabase_not_installed")) from exc

    return create_client(config.url, config.client_key)


def _serialize_user(user: Any) -> dict[str, Any]:
    if user is None:
        return {}
    if isinstance(user, dict):
        return user
    if hasattr(user, "model_dump"):
        return user.model_dump()
    if hasattr(user, "dict"):
        return user.dict()

    serialized = {}
    for field in ("id", "email", "role", "aud", "app_metadata", "user_metadata"):
        value = getattr(user, field, None)
        if value is not None:
            serialized[field] = value
    return serialized


def _store_auth_session(response: Any) -> dict[str, Any]:
    session = getattr(response, "session", None)
    user = getattr(response, "user", None) or getattr(session, "user", None)
    access_token = getattr(session, "access_token", None)
    refresh_token = getattr(session, "refresh_token", None)

    if not access_token or user is None:
        raise RuntimeError(t("auth.error.no_session"))

    user_data = _serialize_user(user)
    st.session_state[SESSION_AUTH_ACCESS_TOKEN_KEY] = access_token
    st.session_state[SESSION_AUTH_REFRESH_TOKEN_KEY] = refresh_token
    st.session_state[SESSION_AUTH_USER_KEY] = user_data
    st.session_state[SESSION_AUTH_VALIDATED_AT_KEY] = time.time()
    return user_data


def clear_auth_state():
    for key in (
        SESSION_AUTH_ACCESS_TOKEN_KEY,
        SESSION_AUTH_REFRESH_TOKEN_KEY,
        SESSION_AUTH_USER_KEY,
        SESSION_AUTH_VALIDATED_AT_KEY,
    ):
        st.session_state.pop(key, None)


def _try_refresh_token() -> dict[str, Any] | None:
    """Tenta renovar a sessao usando o refresh_token armazenado.

    Retorna os dados do usuario atualizados em caso de sucesso, ou None se falhar.
    O estado de sessao e limpo em caso de falha definitiva.
    """
    refresh_token = st.session_state.get(SESSION_AUTH_REFRESH_TOKEN_KEY)
    if not refresh_token:
        clear_auth_state()
        return None

    try:
        client = _create_supabase_client()
        response = client.auth.refresh_session(refresh_token)
        return _store_auth_session(response)
    except Exception:
        clear_auth_state()
        return None


def sign_in_with_password(email: str, password: str) -> dict[str, Any]:
    """Autentica o usuario com e-mail e senha.

    Raises:
        RuntimeError: se as credenciais forem invalidas, e-mail nao confirmado,
                      ou qualquer falha de rede/configuracao.
    """
    if not email or not password:
        raise RuntimeError(t("auth.error.fill_credentials"))

    client = _create_supabase_client()
    try:
        response = client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as exc:
        msg = str(exc).lower()
        if "invalid login credentials" in msg or "invalid_credentials" in msg:
            raise RuntimeError(t("auth.error.invalid_credentials")) from exc
        if "email not confirmed" in msg:
            raise RuntimeError(t("auth.error.email_not_confirmed")) from exc
        if "rate limit" in msg or "too many requests" in msg:
            raise RuntimeError(t("auth.error.rate_limit")) from exc
        raise RuntimeError(t("auth.error.signin_failed", error=exc)) from exc

    return _store_auth_session(response)


def sign_up_with_password(email: str, password: str) -> bool:
    """Cadastra um novo usuario com e-mail e senha.

    Retorna True se o cadastro foi realizado e confirmacao de e-mail foi enviada,
    ou False se o usuario ja existia (sem revelar isso explicitamente ao cliente).

    Raises:
        RuntimeError: em caso de senha fraca, e-mail invalido ou erro de rede.
    """
    if not email or not password:
        raise RuntimeError(t("auth.error.fill_credentials"))
    if len(password) < 6:
        raise RuntimeError(t("auth.error.password_too_short"))

    client = _create_supabase_client()
    try:
        client.auth.sign_up({"email": email, "password": password})
        return True
    except Exception as exc:
        msg = str(exc).lower()
        if "password" in msg and ("weak" in msg or "short" in msg):
            raise RuntimeError(t("auth.error.weak_password")) from exc
        if "rate limit" in msg or "too many requests" in msg:
            raise RuntimeError(t("auth.error.signup_rate_limit")) from exc
        if "invalid email" in msg:
            raise RuntimeError(t("auth.error.invalid_email")) from exc
        raise RuntimeError(t("auth.error.signup_failed", error=exc)) from exc


def get_authenticated_user() -> dict[str, Any] | None:
    """Retorna o usuario autenticado da sessao atual.

    Fluxo:
      1. Se o token ainda esta dentro do TTL de validacao retorna cache.
      2. Se o token esta proximo da expiracao (< _TOKEN_REFRESH_MARGIN_SECONDS)
         ou expirou o TTL tenta renovar via refresh_token.
      3. Se a renovacao falhar limpa estado e retorna None.
    """
    if not is_auth_enabled():
        return None

    access_token = st.session_state.get(SESSION_AUTH_ACCESS_TOKEN_KEY)
    cached_user = st.session_state.get(SESSION_AUTH_USER_KEY)
    validated_at = st.session_state.get(SESSION_AUTH_VALIDATED_AT_KEY, 0.0)

    if not access_token:
        return None

    elapsed = time.time() - validated_at

    # Dentro do TTL: retorna cache sem nenhuma chamada de rede.
    if cached_user and elapsed < AUTH_VALIDATION_TTL_SECONDS:
        return cached_user

    # Fora do TTL: revalida o token com o Supabase.
    # Se o token estiver proximo de expirar, preferimos fazer refresh logo.
    try:
        client = _create_supabase_client()
        response = client.auth.get_user(access_token)
    except Exception:
        # Token invalido ou expirado: tenta renovar com o refresh_token.
        return _try_refresh_token()

    user = getattr(response, "user", None)
    if user is None:
        return _try_refresh_token()

    user_data = _serialize_user(user)
    st.session_state[SESSION_AUTH_USER_KEY] = user_data
    st.session_state[SESSION_AUTH_VALIDATED_AT_KEY] = time.time()
    return user_data


def get_authenticated_email(user: dict[str, Any] | None) -> str | None:
    if not user:
        return None
    return user.get("email")


def is_admin_user(user: dict[str, Any] | None) -> bool:
    email = get_authenticated_email(user)
    if not email:
        return False
    return email.strip().lower() in get_auth_config().admin_emails


def get_user_role_key(user: dict[str, Any] | None) -> str:
    """Retorna a chave i18n do papel do usuario para ser resolvida via t()."""
    return "sidebar.role_admin" if is_admin_user(user) else "sidebar.role_user"


def logout():
    """Encerra a sessao local. Nao invalida o token no servidor Supabase."""
    clear_auth_state()


def render_login_gate():
    config = get_auth_config()

    st.title(t("login.title"))
    st.caption(t("login.caption"))

    if not config.url or not config.client_key:
        st.error(t("login.error_credentials_missing"))
        st.info(t("login.info_configure_secrets"))
        st.code(
            "[supabase]\n"
            "enabled = true\n"
            'url = "https://YOUR-PROJECT.supabase.co"\n'
            'publishable_key = "YOUR_PUBLISHABLE_KEY"\n'
            'admin_emails = ["admin@example.com"]\n'
        )
        return

    _, center_col, _ = st.columns([1, 1.2, 1])
    with center_col:
        tab_labels = [t("login.tab_signin"), t("login.tab_signup")] if config.allow_signup else [t("login.tab_signin")]
        tabs = st.tabs(tab_labels)

        # --- Sign in tab ---
        with tabs[0]:
            with st.form("supabase_login_form", clear_on_submit=False):
                email_login = st.text_input(t("login.email"), key="login_email")
                password_login = st.text_input(t("login.password"), type="password", key="login_password")
                submitted_login = st.form_submit_button(t("login.signin_button"), type="primary", use_container_width=True)

            if submitted_login:
                try:
                    sign_in_with_password(email=email_login, password=password_login)
                except RuntimeError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error(t("login.unexpected_error", error=exc))
                else:
                    st.success(t("login.signin_success"))
                    st.rerun()

        # --- Sign up tab ---
        if config.allow_signup:
            with tabs[1]:
                st.caption(t("login.signup_caption"))
                with st.form("supabase_signup_form", clear_on_submit=True):
                    email_signup = st.text_input(t("login.email"), key="signup_email")
                    password_signup = st.text_input(
                        t("login.password"), type="password", key="signup_password",
                        help=t("login.password_help"),
                    )
                    password_confirm = st.text_input(t("login.password_confirm"), type="password", key="signup_password_confirm")
                    submitted_signup = st.form_submit_button(t("login.signup_button"), type="primary", use_container_width=True)

                if submitted_signup:
                    if password_signup != password_confirm:
                        st.error(t("login.passwords_mismatch"))
                    else:
                        try:
                            sign_up_with_password(email=email_signup, password=password_signup)
                        except RuntimeError as exc:
                            st.error(str(exc))
                        except Exception as exc:
                            st.error(t("login.unexpected_error", error=exc))
                        else:
                            st.success(t("login.signup_success"))
