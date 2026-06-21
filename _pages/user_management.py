"""
CarbonLens V7 — User Management (Tier 5 Multi-Tenant)
Role-based access: Admin / Analyst / Viewer
Organization-level data isolation, invite flow, permission matrix, audit log.
"""

import streamlit as st
import pandas as pd
import utils.auth as auth
import utils.state as S
from components.ui import page_header, kpi_card, insight_panel, card_start, card_end, divider

ROLE_META = {
    "admin":   {"label":"Administrator","color":"#6366F1","bg":"#EEF2FF",
                "perms":["All pages","Data upload","User management","Export","Delete data"]},
    "analyst": {"label":"Analyst",      "color":"#0EA5E9","bg":"#E0F2FE",
                "perms":["All analysis pages","Data upload","Export","No user management"]},
    "viewer":  {"label":"Viewer",       "color":"#64748B","bg":"#F1F5F9",
                "perms":["Dashboard","ESG Analytics (read)","GRI Gap","No upload","No export"]},
}

PERMISSION_MATRIX = {
    "Page Access": {
        "Dashboard":          {"admin":True, "analyst":True,  "viewer":True},
        "ESG Analytics":      {"admin":True, "analyst":True,  "viewer":True},
        "Carbon Accounting":  {"admin":True, "analyst":True,  "viewer":False},
        "AI Consultant":      {"admin":True, "analyst":True,  "viewer":False},
        "Scenario Simulator": {"admin":True, "analyst":True,  "viewer":False},
        "Benchmarking":       {"admin":True, "analyst":True,  "viewer":True},
        "GIS Intelligence":   {"admin":True, "analyst":True,  "viewer":True},
        "POJK 51 / GRI Gap":  {"admin":True, "analyst":True,  "viewer":True},
        "Supplier Scorecard": {"admin":True, "analyst":True,  "viewer":False},
        "User Management":    {"admin":True, "analyst":False, "viewer":False},
    },
    "Actions": {
        "Upload CSV data":    {"admin":True, "analyst":True,  "viewer":False},
        "Edit S+G inputs":    {"admin":True, "analyst":True,  "viewer":False},
        "Export reports":     {"admin":True, "analyst":True,  "viewer":False},
        "Generate PDF":       {"admin":True, "analyst":True,  "viewer":False},
        "Manage users":       {"admin":True, "analyst":False, "viewer":False},
        "Delete data":        {"admin":True, "analyst":False, "viewer":False},
        "Change org profile": {"admin":True, "analyst":False, "viewer":False},
    },
}

def _perm_icon(val: bool) -> str:
    return "✅" if val else "○"


def render():
    S.init()
    page_header(
        title="User Management",
        subtitle="Role-based access control · Organization isolation · Audit log · Multi-tenant",
        badge="Admin Console", badge_type="slate",
    )

    if not auth.can("can_manage_users"):
        st.error("🔒 Administrator role required to access this page.")
        insight_panel([{"icon":"🔑","type":"warn",
            "text":"Hubungi administrator organisasi Anda untuk mendapatkan akses ke halaman ini."}])
        return

    users = auth._load_users()
    current = auth.current_user() or {}
    role_counts = {}
    for u in users.values():
        role_counts[u["role"]] = role_counts.get(u["role"],0) + 1

    # ── KPIs ─────────────────────────────────────────────────────────────────
    k1,k2,k3,k4,k5 = st.columns(5, gap="medium")
    with k1: kpi_card("Total Users",  str(len(users)),                      icon="👥", icon_bg="#E0F2FE")
    with k2: kpi_card("Admins",       str(role_counts.get("admin",0)),       icon="🔑", icon_bg="#EEF2FF",
                       badge="Full access", badge_type="indigo")
    with k3: kpi_card("Analysts",     str(role_counts.get("analyst",0)),     icon="🔬", icon_bg="#ECFEFF",
                       badge="Upload + export", badge_type="sky")
    with k4: kpi_card("Viewers",      str(role_counts.get("viewer",0)),      icon="👁️", icon_bg="#F1F5F9",
                       badge="Read only", badge_type="slate")
    with k5:
        org = S.get("company_name","—") or "—"
        kpi_card("Organization", org[:16]+(""if len(org)<=16 else "…"), icon="🏢", icon_bg="#F5F3FF",
                  badge=f"Slot {S.get_active_slot()+1}", badge_type="purple")

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👥 Users", "➕ Add / Invite", "🔐 Permission Matrix", "📋 Audit Log", "🏢 Org Settings"
    ])

    # ── Tab 1: Users ─────────────────────────────────────────────────────────
    with tab1:
        card_start("Platform Users", "Manage roles and access")

        search = st.text_input("🔍 Filter users", placeholder="name, username, email…",
                                key="um_search", label_visibility="collapsed")

        for username, udata in users.items():
            if search and search.lower() not in (username + udata.get("name","") + udata.get("email","")).lower():
                continue

            role      = udata.get("role","viewer")
            rm        = ROLE_META.get(role, ROLE_META["viewer"])
            is_self   = current.get("username") == username
            last_login= udata.get("last_login","—")

            you_suffix = " (you)" if is_self else ""
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:14px;padding:10px 0 6px;">
                <div style="width:36px;height:36px;border-radius:50%;background:{rm['bg']};
                     display:flex;align-items:center;justify-content:center;
                     font-size:14px;font-weight:700;color:{rm['color']};flex-shrink:0;">
                    {udata.get('name','?')[0].upper()}
                </div>
                <div style="flex:1;min-width:0;">
                    <div style="font-size:13px;font-weight:700;color:#0F172A;">
                        {udata.get('name','—')}{you_suffix}
                    </div>
                    <div style="font-size:10px;color:#94A3B8;">
                        @{username} · {udata.get('email','—')} · Last login: {last_login}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_r, col_del = st.columns([2,1], gap="small")
            with col_r:
                new_role = st.selectbox("Role", ["admin","analyst","viewer"],
                    index=["admin","analyst","viewer"].index(role),
                    key=f"role_{username}", label_visibility="collapsed",
                    format_func=lambda r: ROLE_META[r]["label"],
                    disabled=is_self)
                if new_role != role and not is_self:
                    users[username]["role"] = new_role
                    auth._save_users(users)
                    auth._audit_log("role_change", current.get("username","?"),
                                    f"Changed {username}: {role} → {new_role}")
                    st.rerun()
            with col_del:
                if not is_self:
                    if st.button("🗑️ Remove", key=f"del_{username}", use_container_width=True):
                        del users[username]
                        auth._save_users(users)
                        auth._audit_log("user_deleted", current.get("username","?"),
                                        f"Deleted: {username}")
                        st.success(f"User {username} removed.")
                        st.rerun()

            st.markdown('<div style="height:1px;background:#F8FAFC;margin:6px 0 4px;"></div>', unsafe_allow_html=True)

        card_end()

    # ── Tab 2: Add / Invite ───────────────────────────────────────────────────
    with tab2:
        col_add, col_roles = st.columns([1.2, 1], gap="medium")

        with col_add:
            card_start("Add New User", "New user gets instant access on next login")
            new_username = st.text_input("Username *", placeholder="jdoe", key="um_new_user")
            new_name     = st.text_input("Full Name *", placeholder="John Doe", key="um_new_name")
            new_email    = st.text_input("Email", placeholder="jdoe@company.com", key="um_new_email")
            new_role     = st.selectbox("Role *", ["viewer","analyst","admin"], key="um_new_role",
                                         format_func=lambda r: f"{ROLE_META[r]['label']} — {', '.join(ROLE_META[r]['perms'][:2])}")
            new_password = st.text_input("Temporary Password *", type="password", key="um_new_pw")

            if st.button("➕  Add User", type="primary", use_container_width=True, key="um_add_btn"):
                if not new_username.strip() or not new_name.strip() or not new_password:
                    st.error("Username, name, dan password wajib diisi.")
                elif new_username in users:
                    st.error(f"Username '{new_username}' sudah digunakan.")
                else:
                    users[new_username] = {
                        "name":     new_name.strip(),
                        "password": auth._hash(new_password),
                        "role":     new_role,
                        "email":    new_email.strip(),
                        "last_login": "—",
                        "must_change_password": True,
                    }
                    auth._save_users(users)
                    auth._audit_log("user_created", current.get("username","?"),
                                    f"Created: {new_username} ({new_role})")
                    st.success(f"✅ User '{new_username}' berhasil ditambahkan sebagai {ROLE_META[new_role]['label']}.")
                    st.rerun()
            card_end()

        with col_roles:
            card_start("Role Overview")
            for role, rm in ROLE_META.items():
                st.markdown(f"""
                <div style="padding:10px 12px;background:{rm['bg']};border-radius:8px;
                     border-left:3px solid {rm['color']};margin-bottom:8px;">
                    <div style="font-size:12px;font-weight:700;color:{rm['color']};
                         margin-bottom:4px;">{rm['label']}</div>
                    <div style="font-size:11px;color:#374151;">
                        {'<br>'.join(['✓ '+p for p in rm['perms']])}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            card_end()

    # ── Tab 3: Permission Matrix ───────────────────────────────────────────────
    with tab3:
        card_start("Permission Matrix", "Lengkap per fitur — Admin / Analyst / Viewer")

        for category, perms in PERMISSION_MATRIX.items():
            st.markdown(f"""
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
                 color:#94A3B8;margin:14px 0 8px;">{category}</div>
            """, unsafe_allow_html=True)

            rows = [{"Feature": feat,
                     "Admin": _perm_icon(vals["admin"]),
                     "Analyst": _perm_icon(vals["analyst"]),
                     "Viewer": _perm_icon(vals["viewer"])}
                    for feat, vals in perms.items()]
            st.dataframe(pd.DataFrame(rows), use_container_width=True,
                         hide_index=True, height=min(360, 38+36*len(rows)))

        card_end()

        insight_panel([
            {"icon":"🔑","type":"info",
             "text":"<strong>Admin</strong> memiliki akses penuh termasuk user management dan penghapusan data. "
                    "Minimal 1 admin harus aktif per organisasi — tidak bisa menghapus admin terakhir."},
            {"icon":"🔬","type":"info",
             "text":"<strong>Analyst</strong> cocok untuk tim sustainability yang perlu upload dan analisis data "
                    "tapi tidak perlu akses manajemen user."},
            {"icon":"👁️","type":"info",
             "text":"<strong>Viewer</strong> ideal untuk manajemen senior atau auditor eksternal yang hanya "
                    "perlu melihat dashboard dan laporan, tanpa bisa mengubah data."},
        ])

    # ── Tab 4: Audit Log ──────────────────────────────────────────────────────
    with tab4:
        card_start("Audit Log", "Last 100 actions — user management, data changes, exports")

        log_entries = auth.get_audit_log(100)
        if not log_entries:
            st.info("Belum ada aktivitas tercatat.")
        else:
            log_df = pd.DataFrame(log_entries)
            if "ts" in log_df.columns:
                log_df["ts"] = log_df["ts"].str[:19].str.replace("T"," ")
                log_df = log_df.rename(columns={"ts":"Timestamp","user":"User",
                                                  "action":"Action","detail":"Detail"})

            action_filter = st.multiselect(
                "Filter by action", log_df["Action"].unique().tolist() if "Action" in log_df.columns else [],
                key="um_log_filter", label_visibility="collapsed",
                placeholder="Filter action type…"
            )
            if action_filter:
                log_df = log_df[log_df["Action"].isin(action_filter)]

            st.dataframe(log_df, use_container_width=True, height=380, hide_index=True)
            col_dl, _ = st.columns([1,3])
            with col_dl:
                st.download_button("⬇️  Export Audit Log CSV",
                    data=log_df.to_csv(index=False).encode(),
                    file_name="carbonlens_audit_log.csv", mime="text/csv",
                    use_container_width=True)

        card_end()

    # ── Tab 5: Org Settings ───────────────────────────────────────────────────
    with tab5:
        card_start("Organization Settings", "Multi-tenant config — data isolation per slot")

        companies = S.get_company_summary()
        st.markdown(f"""
        <div style="background:#F0F9FF;border:1px solid #BAE6FD;border-radius:10px;
             padding:14px 18px;margin-bottom:16px;font-size:12px;color:#0C4A6E;">
            <strong>Multi-Tenant Mode</strong> — CarbonLens mendukung hingga
            <strong>{len(companies)} organization slots</strong>. Setiap slot memiliki data ESG,
            konfigurasi, dan user access yang terpisah sepenuhnya. Gunakan Company Switcher
            di sidebar untuk berpindah antar organisasi.
        </div>
        """, unsafe_allow_html=True)

        for co in companies:
            slot       = co["slot"]
            is_act     = co["slot"] == S.get_active_slot()
            bg         = "#F0F9FF" if is_act else "#F8FAFC"
            border     = "#0EA5E9" if is_act else "#E2E8F0"
            icon       = "🏢" if co["setup"] else "○"
            name_label = co["name"] if co["setup"] else f"Slot {slot+1} — Empty"
            active_tag = ' <span style="font-size:10px;color:#0EA5E9;">(active)</span>' if is_act else ""
            sub_label  = f"ESG Grade: {co['grade']} · Slot {slot+1}" if co["setup"] else "No organization configured"
            active_badge = '<div style="font-size:10px;font-weight:700;color:#10B981;white-space:nowrap;">● Active</div>' if is_act else ""

            card_html = (
                f'<div style="background:{bg};border:1.5px solid {border};border-radius:10px;'
                f'padding:12px 16px;margin-bottom:8px;display:flex;align-items:center;gap:14px;">'
                f'<div style="font-size:22px;">{icon}</div>'
                f'<div style="flex:1;">'
                f'<div style="font-size:13px;font-weight:700;color:#0F172A;">{name_label}{active_tag}</div>'
                f'<div style="font-size:10px;color:#94A3B8;">{sub_label}</div>'
                f'</div>'
                f'{active_badge}'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#FFF7ED;border:1px solid #FED7AA;border-radius:8px;
             padding:10px 14px;font-size:12px;color:#92400E;">
            <strong>Data Isolation:</strong> Emisi, profil perusahaan, data S+G, dan semua konfigurasi
            tersimpan terpisah per slot. Reset satu slot tidak memengaruhi slot lain.
        </div>
        """, unsafe_allow_html=True)
        card_end()
