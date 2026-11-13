from datetime import datetime
from io import BytesIO
import os
import sqlite3
import pandas as pd
import pytz
import requests
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")
from PIL import Image as PILImage

# URL Web App dari Google Apps Script Anda
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycby_YGCckSCAKhEOxlOMvhD0_dNUn4OM-lOyYLRzbE7aUzhnK5v9BU6ywVf6n1v-U7Y/exec"


def backup_ke_gsh_otomatis(data_dict):
  try:
    requests.post(WEBHOOK_URL, json=data_dict)
  except Exception as e:
    print(f"Gagal backup: {e}")


# Zona Waktu WIB
TZ_WIB = pytz.timezone("Asia/Jakarta")
waktu_sekarang = datetime.now(TZ_WIB)
hari_ini = waktu_sekarang.strftime("%Y-%m-%d")

# Mapping Daftar Promotor dan Zona
PROMOTOR_ZONA = {
    "Arif Yuliadi": "Bawean",
    "Nur Muhammad Khoirul Firmansyah": "Bawean",
}

# Daftar Brand yang Tersedia
DAFTAR_BRAND = [
    "D.Super 12",
    "D.76 Apel",
    "D.76 Apel Royal",
    "Black Matcha K12",
    "Black Matcha Siro",
    "Black Matcha Kuro",
    "Djarum 76 Aksara",
]

# Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="Form Entry Laporan Kanvas",
    page_icon="📋",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Styling CSS agar tampilan lebih rapi
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f8fafc;
    }
    h1, h2, h3 {
        color: #0f172a;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        width: 100%;
    }
    div[data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #e2e8f0;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ====================================================
# INISIALISASI & MIGRASI DATABASE SQLITE
# ====================================================
DB_NAME = "laporan_kanvas.db"


def inisialisasi_database():
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS kanvas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal TEXT,
            nama_promotor TEXT,
            zona TEXT,
            brand TEXT,
            canvas_plan INTEGER,
            outlet_beli_ada INTEGER,
            outlet_ks_tb INTEGER,
            outlet_ks_b INTEGER,
            outlet_tb_ada_a INTEGER,
            outlet_tb_ada_p INTEGER,
            outlet_tb_ks INTEGER,
            omset_bungkus INTEGER,
            promsus_10_1 INTEGER,
            promsus_3_1 INTEGER,
            promsus_2_1 INTEGER,
            promsus_1_1 INTEGER,
            promsus_n_mie_instan INTEGER,
            outlet_buka_ecer INTEGER,
            jumlah_rokok_sampling INTEGER,
            jumlah_konsumen_trial INTEGER,
            direct_selling INTEGER,
            jumlah_setoran INTEGER,
            waktu_submit TEXT
        )
    """)
  conn.commit()

  cursor.execute("PRAGMA table_info(kanvas)")
  columns = [col[1] for col in cursor.fetchall()]

  if "pic" in columns and "nama_promotor" not in columns:
    cursor.execute("ALTER TABLE kanvas RENAME COLUMN pic TO nama_promotor")
  if "zona" not in columns:
    cursor.execute("ALTER TABLE kanvas ADD COLUMN zona TEXT")
  if "jumlah_setoran" not in columns:
    cursor.execute("ALTER TABLE kanvas ADD COLUMN jumlah_setoran INTEGER DEFAULT 0")

  kolom_promsus = {
      "promsus_10_1": "INTEGER",
      "promsus_3_1": "INTEGER",
      "promsus_2_1": "INTEGER",
      "promsus_1_1": "INTEGER",
      "promsus_n_mie_instan": "INTEGER",
      "outlet_buka_ecer": "INTEGER",
      "jumlah_rokok_sampling": "INTEGER",
      "jumlah_konsumen_trial": "INTEGER",
      "direct_selling": "INTEGER",
  }
  for col_name, col_type in kolom_promsus.items():
    if col_name not in columns:
      cursor.execute(
          f"ALTER TABLE kanvas ADD COLUMN {col_name} {col_type} DEFAULT 0"
      )

  conn.commit()
  conn.close()


inisialisasi_database()


def muat_data():
  conn = sqlite3.connect(DB_NAME)
  try:
    df = pd.read_sql_query(
        """
            SELECT id AS ID, tanggal AS Tanggal, nama_promotor AS [Nama Promotor], zona AS Zona, brand AS Brand, canvas_plan AS [Canvas Plan],
                   outlet_beli_ada AS [Outlet Beli Ada], outlet_ks_tb AS [Outlet Ks Tb], 
                   outlet_ks_b AS [Outlet Ks B], outlet_tb_ada_a AS [Outlet TB Ada A], 
                   outlet_tb_ada_p AS [Outlet TB Ada P], outlet_tb_ks AS [Outlet TB Ks], 
                   omset_bungkus AS [Omset (Bungkus)], 
                   promsus_10_1 AS [Promsus 10+1],
                   promsus_3_1 AS [Promsus 3+1],
                   promsus_2_1 AS [Promsus 2+1],
                   promsus_1_1 AS [Promsus 1+1],
                   promsus_n_mie_instan AS [N+ Mie Instan],
                   outlet_buka_ecer AS [Outlet Buka Ecer],
                   jumlah_rokok_sampling AS [Jumlah Rokok Sampling],
                   jumlah_konsumen_trial AS [Jumlah Konsumen Trial],
                   direct_selling AS [Direct Selling],
                   jumlah_setoran AS [Jumlah Setoran (Rp)],
                   waktu_submit AS [Waktu Submit]
            FROM kanvas
            ORDER BY waktu_submit DESC
        """,
        conn,
    )
  except Exception:
    df = pd.DataFrame()
  conn.close()
  return df


def buat_gambar_rekap(df, judul):
  """Membuat gambar tabel rekapitulasi untuk diunduh (PNG/JPEG).

  Teks 2 baris dalam kotak berbingkai di kiri, logo di kanan, tabel rapi.
  """
  has_logo = os.path.exists("76aksara.png")

  fig_height = 20.0 if has_logo else 18.5
  fig = plt.figure(figsize=(18, fig_height), facecolor="white")

  # ===== 1. JUDUL (Di bagian paling atas, rata tengah) =====
  ax_title = fig.add_axes([0.0, 0.945, 1.0, 0.040])
  ax_title.axis("off")
  ax_title.text(
      0.5,
      0.5,
      judul,
      ha="center",
      va="center",
      fontsize=32,
      fontweight="bold",
      color="#0f172a",
      fontfamily="sans-serif",
  )

  # ===== 2. HEADER ATAS: TEKS BERKOTAK DI KIRI & LOGO DI KANAN =====
  if has_logo:
    ax_text = fig.add_axes([0.02, 0.840, 0.30, 0.095])
    ax_text.axis("off")

    ax_text.text(
        0.5,
        0.5,
        "DSO\nSURABAYA BARAT",
        ha="center",
        va="center",
        fontsize=22,
        fontweight="bold",
        color="#0f172a",
        fontfamily="sans-serif",
        linespacing=1.2,
        bbox=dict(
            boxstyle="round,pad=0.5",
            facecolor="#f1f5f9",
            edgecolor="#64748b",
            linewidth=2.0,
        ),
    )

    ax_logo = fig.add_axes([0.34, 0.840, 0.67, 0.095])
    ax_logo.axis("off")
    try:
      logo_img = PILImage.open("76aksara.png")
      ax_logo.imshow(logo_img, aspect="auto")
      ax_logo.set_xlim(0, logo_img.width)
      ax_logo.set_ylim(logo_img.height, 0)
    except Exception:
      ax_logo.text(
          0.5,
          0.5,
          "Logo 76aksara.png",
          ha="center",
          va="center",
          fontsize=13,
          color="#64748b",
      )

    table_bottom = 0.02
    table_height = 0.800
  else:
    table_bottom = 0.03
    table_height = 0.900

  # ===== 3. TABEL DATA REKAP =====
  ax_table = fig.add_axes([0.02, table_bottom, 0.99, table_height])
  ax_table.axis("off")

  cell_text = [[str(v) for v in row] for row in df.values.tolist()]
  col_labels = [str(c) for c in df.columns]
  row_labels = [str(r) for r in df.index]

  table = ax_table.table(
      cellText=cell_text,
      colLabels=col_labels,
      rowLabels=row_labels,
      loc="upper center",
      cellLoc="center",
      bbox=[0, 0, 1, 1],
  )
  table.auto_set_font_size(False)
  table.set_fontsize(26)
  table.scale(1.0, 1.85)

  for (row, col), cell in table.get_celld().items():
    cell.set_edgecolor("#64748b")
    cell.set_linewidth(2.0)
    cell.PAD = 0.12

    if row == 0 and col == -1:
      cell.set_facecolor("#ffffff")
      cell.set_text_props(text="")
    elif row == 0:
      cell.set_text_props(weight="bold", color="#0f172a", fontsize=24)
      cell.set_facecolor("#e2e8f0")
    elif col == -1:
      cell.set_text_props(
          weight="bold", color="#1e293b", fontsize=22, ha="left"
      )
      cell.set_facecolor("#f1f5f9")
    else:
      cell.set_facecolor("#ffffff")
      cell.set_text_props(weight="bold", color="#0f172a", fontsize=22)

  buf = BytesIO()
  plt.savefig(
      buf,
      format="png",
      bbox_inches="tight",
      dpi=180,
      facecolor="white",
      edgecolor="none",
      pad_inches=0.08,
  )
  buf.seek(0)
  plt.close(fig)
  return buf


# Notifikasi sukses
if "notifikasi_sukses" in st.session_state:
  st.balloons()
  st.success(st.session_state.pop("notifikasi_sukses"))

st.markdown(
    "<h2 style='text-align: center;'>📋 Form Entry Laporan Kanvas</h2>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: #64748b;'>Sistem Perekaman Data"
    " Kanvas Lapangan</p>",
    unsafe_allow_html=True,
)


def simpan_ke_database(data_preview):
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute(
      """
        INSERT INTO kanvas (
            tanggal, nama_promotor, zona, brand, canvas_plan, outlet_beli_ada, outlet_ks_tb, 
            outlet_ks_b, outlet_tb_ada_a, outlet_tb_ada_p, outlet_tb_ks, 
            omset_bungkus, promsus_10_1, promsus_3_1, promsus_2_1, promsus_1_1, 
            promsus_n_mie_instan, outlet_buka_ecer, jumlah_rokok_sampling, jumlah_konsumen_trial, 
            direct_selling, jumlah_setoran, waktu_submit
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
      (
          data_preview["tanggal"],
          data_preview["nama_promotor"],
          data_preview["zona"],
          data_preview["brand"],
          data_preview["canvas_plan"],
          data_preview["outlet_beli_ada"],
          data_preview["outlet_ks_tb"],
          data_preview["outlet_ks_b"],
          data_preview["outlet_tb_ada_a"],
          data_preview["outlet_tb_ada_p"],
          data_preview["outlet_tb_ks"],
          data_preview["omset_bungkus"],
          data_preview["promsus_10_1"],
          data_preview["promsus_3_1"],
          data_preview["promsus_2_1"],
          data_preview["promsus_1_1"],
          data_preview["promsus_n_mie_instan"],
          data_preview["outlet_buka_ecer"],
          data_preview["jumlah_rokok_sampling"],
          data_preview["jumlah_konsumen_trial"],
          data_preview["direct_selling"],
          data_preview["jumlah_setoran"],
          data_preview["waktu_submit"],
      ),
  )
  conn.commit()
  conn.close()
  backup_ke_gsh_otomatis(data_preview)


# ====================================================
# FORM ENTRY DATA BARU
# ====================================================
if "form_preview_data" not in st.session_state:
  st.session_state["form_preview_data"] = None

if st.session_state["form_preview_data"] is None:
  with st.form("form_laporan_kanvas"):
    st.markdown("### 📝 Masukkan Data Laporan Baru")

    col1, col2 = st.columns(2)
    with col1:
      tanggal_entry = st.date_input("Date", value=datetime.now(TZ_WIB).date())
      promotor_entry = st.selectbox("Nama Promotor", list(PROMOTOR_ZONA.keys()))
      brand_entry = st.selectbox("Brand", DAFTAR_BRAND)
    with col2:
      zona_otomatis = PROMOTOR_ZONA.get(promotor_entry, "-")
      st.text_input("Zona (Otomatis)", value=zona_otomatis, disabled=True)
      canvas_plan_entry = st.number_input(
          "Canvas Plan", min_value=0, step=1, value=0
      )
      omset_entry = st.number_input(
          "Omset (bungkus)", min_value=0, step=1, value=0
      )

    st.markdown("---")
    st.markdown("#### 📊 Rincian Outlet")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
      outlet_beli_ada = st.number_input(
          "Jumlah Outlet Beli Ada", min_value=0, step=1, value=0
      )
      outlet_ks_tb = st.number_input(
          "Jumlah Outlet Ks Tb", min_value=0, step=1, value=0
      )
    with col_b:
      outlet_ks_b = st.number_input(
          "Jumlah Outlet Ks B", min_value=0, step=1, value=0
      )
      outlet_tb_ada_a = st.number_input(
          "Jumlah Outlet Tidak Beli Ada A", min_value=0, step=1, value=0
      )
    with col_c:
      outlet_tb_ada_p = st.number_input(
          "Jumlah Outlet Tidak Beli Ada P", min_value=0, step=1, value=0
      )
      outlet_tb_ks = st.number_input(
          "Jumlah Outlet Tidak Beli Ks", min_value=0, step=1, value=0
      )

    st.markdown("---")
    st.markdown("#### 🎁 Promosi Khusus (Promsus)")
    p1, p2, p3, p4 = st.columns(4)
    with p1:
      promsus_10_1 = st.number_input("10+1", min_value=0, step=1, value=0)
      promsus_1_1 = st.number_input("1+1", min_value=0, step=1, value=0)
    with p2:
      promsus_3_1 = st.number_input("3+1", min_value=0, step=1, value=0)
      promsus_n_mie = st.number_input(
          "N+ Mie Instan", min_value=0, step=1, value=0
      )
    with p3:
      promsus_2_1 = st.number_input("2+1", min_value=0, step=1, value=0)
      outlet_buka_ecer = st.number_input(
          "Outlet Buka Ecer", min_value=0, step=1, value=0
      )
    with p4:
      jml_sampling = st.number_input(
          "Jumlah Rokok Sampling", min_value=0, step=1, value=0
      )
      jml_trial = st.number_input(
          "Jumlah Konsumen Trial", min_value=0, step=1, value=0
      )

    direct_selling = st.number_input("Direct Selling", min_value=0, step=1, value=0)

    st.markdown("---")
    st.markdown("#### 💸 Setoran")
    
    jumlah_setoran_entry = st.number_input(
        "Jumlah Setoran (Rp)", min_value=0, step=500, value=0
    )

    st.markdown("---")
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
      btn_preview = st.form_submit_button("👁️ Lihat Preview", type="secondary")
    with btn_col2:
      btn_langsung_kirim = st.form_submit_button("🚀 Langsung Kirim", type="primary")

    if btn_preview or btn_langsung_kirim:
      if not promotor_entry:
        st.error("❌ Kolom Nama Promotor wajib diisi!")
      else:
        data_sementara = {
            "tanggal": tanggal_entry.strftime("%Y-%m-%d"),
            "nama_promotor": promotor_entry,
            "zona": PROMOTOR_ZONA.get(promotor_entry, ""),
            "brand": brand_entry,
            "canvas_plan": canvas_plan_entry,
            "outlet_beli_ada": outlet_beli_ada,
            "outlet_ks_tb": outlet_ks_tb,
            "outlet_ks_b": outlet_ks_b,
            "outlet_tb_ada_a": outlet_tb_ada_a,
            "outlet_tb_ada_p": outlet_tb_ada_p,
            "outlet_tb_ks": outlet_tb_ks,
            "omset_bungkus": omset_entry,
            "promsus_10_1": promsus_10_1,
            "promsus_3_1": promsus_3_1,
            "promsus_2_1": promsus_2_1,
            "promsus_1_1": promsus_1_1,
            "promsus_n_mie_instan": promsus_n_mie,
            "outlet_buka_ecer": outlet_buka_ecer,
            "jumlah_rokok_sampling": jml_sampling,
            "jumlah_konsumen_trial": jml_trial,
            "direct_selling": direct_selling,
            "jumlah_setoran": jumlah_setoran_entry,
            "waktu_submit": waktu_sekarang.strftime("%Y-%m-%d %H:%M:%S"),
        }

        if btn_preview:
          st.session_state["form_preview_data"] = data_sementara
          st.rerun()
        elif btn_langsung_kirim:
          simpan_ke_database(data_sementara)
          st.session_state["notifikasi_sukses"] = (
              "🎉 Data laporan kanvas berhasil dikirim langsung ke database!"
          )
          st.rerun()

else:
  st.markdown("### 📋 Preview Data Laporan Baru")
  st.info("Periksa kembali data di bawah ini sebelum disimpan ke database.")

  data_preview = st.session_state["form_preview_data"]
  df_preview_view = pd.DataFrame(
      list(data_preview.items()), columns=["Keterangan", "Nilai"]
  )
  st.dataframe(df_preview_view, use_container_width=True, hide_index=True)

  st.markdown("---")
  col_btn1, col_btn2 = st.columns(2)
  with col_btn1:
    if st.button("❌ Batal / Edit Kembali", use_container_width=True):
      st.session_state["form_preview_data"] = None
      st.rerun()
  with col_btn2:
    if st.button(
        "🚀 Konfirmasi & Simpan Laporan", type="primary", use_container_width=True
    ):
      simpan_ke_database(data_preview)
      st.session_state["form_preview_data"] = None
      st.session_state["notifikasi_sukses"] = (
          "🎉 Data laporan kanvas berhasil disimpan ke database!"
      )
      st.rerun()

# ====================================================
# MONITORING STATUS ENTRY HARI INI
# ====================================================
st.markdown("---")
st.markdown("### 🔍 Monitoring Status Entry Promotor Hari Ini")
st.markdown(
    f"<p style='color: #64748b;'>Tanggal Monitoring: <b>{hari_ini}</b></p>",
    unsafe_allow_html=True,
)

df_data_global = muat_data()
df_hari_ini = (
    df_data_global[df_data_global["Tanggal"] == hari_ini]
    if not df_data_global.empty
    else pd.DataFrame()
)
promotor_sudah_entry = (
    df_hari_ini["Nama Promotor"].dropna().unique().tolist()
    if not df_hari_ini.empty
    else []
)

tab_sudah, tab_belum = st.tabs([
    f"✅ Sudah Entry ({len(promotor_sudah_entry)})",
    f"⚠️ Belum Entry ({len(PROMOTOR_ZONA) - len(promotor_sudah_entry)})",
])

with tab_sudah:
  if not df_hari_ini.empty:
    data_sudah_list = [
        {"Nama Promotor": p, "Zona": PROMOTOR_ZONA.get(p, "-")}
        for p in promotor_sudah_entry
    ]
    st.dataframe(pd.DataFrame(data_sudah_list), use_container_width=True)
  else:
    st.info("📭 Belum ada promotor yang melakukan entry laporan pada hari ini.")

with tab_belum:
  daftar_belum_entry = [
      {"Nama Promotor": promotor, "Zona": zona}
      for promotor, zona in PROMOTOR_ZONA.items()
      if promotor not in promotor_sudah_entry
  ]
  if daftar_belum_entry:
    st.dataframe(pd.DataFrame(daftar_belum_entry), use_container_width=True)
  else:
    st.success("🎉 Seluruh promotor telah melakukan entry laporan hari ini.")

# ====================================================
# AREA ADMIN & REKAPITULASI
# ====================================================
st.markdown("---")
st.markdown("### 🔐 Area Khusus Admin (Log & Rekapitulasi)")

if "admin_authenticated" not in st.session_state:
  st.session_state["admin_authenticated"] = False

if not st.session_state["admin_authenticated"]:
  with st.form("form_password_admin"):
    st.info("⚠️ Panel Admin dilindungi password. Silakan masukkan password.")
    password_input = st.text_input("Password Admin:", type="password")
    if st.form_submit_button("🔓 Buka Area Admin", type="primary"):
      if password_input == "admin123":
        st.session_state["admin_authenticated"] = True
        st.rerun()
      else:
        st.error("❌ Password salah!")
else:
  if st.button("🔒 Kunci Kembali Area Admin"):
    st.session_state["admin_authenticated"] = False
    st.rerun()

  st.markdown("### 📊 Panel Admin & Log Laporan Kanvas")
  df_data = muat_data()
  if not df_data.empty:
    st.dataframe(df_data, use_container_width=True)

    st.markdown("---")
    st.markdown("### 🛠️ Manajemen Data (Edit, Unduh, & Hapus)")

    with st.expander("✏️ Edit Entry Data (Koreksi Kesalahan Input)"):
      list_id = df_data["ID"].tolist()
      id_dipilih = st.selectbox("Pilih ID Data yang Ingin Di-edit:", list_id)
      row_edit = df_data[df_data["ID"] == id_dipilih].iloc[0]

      with st.form("form_edit_kanvas"):
        st.markdown(f"#### Edit Data ID #{id_dipilih}")
        e_col1, e_col2 = st.columns(2)
        with e_col1:
          e_tanggal = st.date_input(
              "Tanggal",
              value=datetime.strptime(
                  str(row_edit["Tanggal"]), "%Y-%m-%d"
              ).date(),
          )
          list_promotor = list(PROMOTOR_ZONA.keys())
          idx_promotor = (
              list_promotor.index(row_edit["Nama Promotor"])
              if row_edit["Nama Promotor"] in list_promotor
              else 0
          )
          e_promotor = st.selectbox(
              "Nama Promotor", list_promotor, index=idx_promotor
          )
          idx_brand = (
              DAFTAR_BRAND.index(row_edit["Brand"])
              if row_edit["Brand"] in DAFTAR_BRAND
              else 0
          )
          e_brand = st.selectbox("Brand", DAFTAR_BRAND, index=idx_brand)
        with e_col2:
          e_zona_otomatis = PROMOTOR_ZONA.get(e_promotor, "-")
          st.text_input("Zona (Otomatis)", value=e_zona_otomatis, disabled=True)
          e_canvas_plan = st.number_input(
              "Canvas Plan",
              min_value=0,
              step=1,
              value=int(row_edit["Canvas Plan"]),
          )
          e_omset = st.number_input(
              "Omset (bungkus)",
              min_value=0,
              step=1,
              value=int(row_edit["Omset (Bungkus)"]),
          )

        st.markdown("##### Rincian Outlet")
        e_a, e_b, e_c = st.columns(3)
        with e_a:
          e_outlet_beli_ada = st.number_input(
              "Outlet Beli Ada",
              min_value=0,
              step=1,
              value=int(row_edit["Outlet Beli Ada"]),
          )
          e_outlet_ks_tb = st.number_input(
              "Outlet Ks Tb",
              min_value=0,
              step=1,
              value=int(row_edit["Outlet Ks Tb"]),
          )
        with e_b:
          e_outlet_ks_b = st.number_input(
              "Outlet Ks B",
              min_value=0,
              step=1,
              value=int(row_edit["Outlet Ks B"]),
          )
          e_outlet_tb_ada_a = st.number_input(
              "Outlet TB Ada A",
              min_value=0,
              step=1,
              value=int(row_edit["Outlet TB Ada A"]),
          )
        with e_c:
          e_outlet_tb_ada_p = st.number_input(
              "Outlet TB Ada P",
              min_value=0,
              step=1,
              value=int(row_edit["Outlet TB Ada P"]),
          )
          e_outlet_tb_ks = st.number_input(
              "Outlet TB Ks",
              min_value=0,
              step=1,
              value=int(row_edit["Outlet TB Ks"]),
          )

        st.markdown("##### Promosi Khusus (Promsus)")
        ep1, ep2, ep3, ep4 = st.columns(4)
        with ep1:
          e_promsus_10_1 = st.number_input(
              "10+1", min_value=0, step=1, value=int(row_edit["Promsus 10+1"])
          )
          e_promsus_1_1 = st.number_input(
              "1+1", min_value=0, step=1, value=int(row_edit["Promsus 1+1"])
          )
        with ep2:
          e_promsus_3_1 = st.number_input(
              "3+1", min_value=0, step=1, value=int(row_edit["Promsus 3+1"])
          )
          e_promsus_n_mie = st.number_input(
              "N+ Mie Instan",
              min_value=0,
              step=1,
              value=int(row_edit["N+ Mie Instan"]),
          )
        with ep3:
          e_promsus_2_1 = st.number_input(
              "2+1", min_value=0, step=1, value=int(row_edit["Promsus 2+1"])
          )
          e_outlet_buka_ecer = st.number_input(
              "Outlet Buka Ecer",
              min_value=0,
              step=1,
              value=int(row_edit["Outlet Buka Ecer"]),
          )
        with ep4:
          e_jml_sampling = st.number_input(
              "Jumlah Rokok Sampling",
              min_value=0,
              step=1,
              value=int(row_edit["Jumlah Rokok Sampling"]),
          )
          e_jml_trial = st.number_input(
              "Jumlah Konsumen Trial",
              min_value=0,
              step=1,
              value=int(row_edit["Jumlah Konsumen Trial"]),
          )

        e_direct_selling = st.number_input(
            "Direct Selling",
            min_value=0,
            step=1,
            value=int(row_edit["Direct Selling"]),
        )

        val_setoran_edit = (
            int(row_edit["Jumlah Setoran (Rp)"])
            if "Jumlah Setoran (Rp)" in row_edit and pd.notnull(row_edit["Jumlah Setoran (Rp)"])
            else 0
        )
        e_jumlah_setoran = st.number_input(
            "Jumlah Setoran (Rp)",
            min_value=0,
            step=500,
            value=val_setoran_edit,
        )

        btn_update = st.form_submit_button("💾 Perbarui Data", type="primary")

        if btn_update:
          if not e_promotor:
            st.error("❌ Nama Promotor tidak boleh kosong!")
          else:
            tgl_edit_str = e_tanggal.strftime("%Y-%m-%d")
            zona_edit_final = PROMOTOR_ZONA.get(e_promotor, "")

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                """
                            UPDATE kanvas
                            SET tanggal = ?, nama_promotor = ?, zona = ?, brand = ?, canvas_plan = ?,
                                outlet_beli_ada = ?, outlet_ks_tb = ?, outlet_ks_b = ?, outlet_tb_ada_a = ?,
                                outlet_tb_ada_p = ?, outlet_tb_ks = ?, omset_bungkus = ?, promsus_10_1 = ?,
                                promsus_3_1 = ?, promsus_2_1 = ?, promsus_1_1 = ?, promsus_n_mie_instan = ?,
                                outlet_buka_ecer = ?, jumlah_rokok_sampling = ?, jumlah_konsumen_trial = ?, 
                                direct_selling = ?, jumlah_setoran = ?
                            WHERE id = ?
                        """,
                (
                    tgl_edit_str,
                    e_promotor,
                    zona_edit_final,
                    e_brand,
                    e_canvas_plan,
                    e_outlet_beli_ada,
                    e_outlet_ks_tb,
                    e_outlet_ks_b,
                    e_outlet_tb_ada_a,
                    e_outlet_tb_ada_p,
                    e_outlet_tb_ks,
                    e_omset,
                    e_promsus_10_1,
                    e_promsus_3_1,
                    e_promsus_2_1,
                    e_promsus_1_1,
                    e_promsus_n_mie,
                    e_outlet_buka_ecer,
                    e_jml_sampling,
                    e_jml_trial,
                    e_direct_selling,
                    e_jumlah_setoran,
                    id_dipilih,
                ),
            )
            conn.commit()
            conn.close()

            st.session_state["notifikasi_sukses"] = (
                f"✏️ Data ID #{id_dipilih} berhasil diperbarui!"
            )
            st.rerun()

    col_d, col_h = st.columns(2)
    with col_d:
      st.markdown("#### 📥 Unduh Laporan")
      opsi_unduh = st.selectbox(
          "Pilih Rentang Data:", ["Semua Data", "Hari Ini"]
      )
      df_export = (
          df_data[df_data["Tanggal"] == hari_ini]
          if opsi_unduh == "Hari Ini"
          else df_data.copy()
      )
      output = BytesIO()
      with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_export.to_excel(writer, index=False, sheet_name="Laporan Kanvas")

      st.download_button(
          label=f"💾 Download Excel ({opsi_unduh})",
          data=output.getvalue(),
          file_name=(
              f"laporan_kanvas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
          ),
          mime=(
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          ),
          use_container_width=True,
      )

    with col_h:
      st.markdown("#### 🗑️ Hapus Data")
      opsi_hapus = st.selectbox(
          "Pilih Data yang Dihapus:", ["Hapus per Row (ID)", "Hari Ini", "Semua Data"], key="opt_hapus"
      )
      
      if opsi_hapus == "Hapus per Row (ID)":
        id_hapus_pilihan = st.selectbox("Pilih ID Baris yang Ingin Dihapus:", df_data["ID"].tolist(), key="select_id_hapus")
        if st.button("🔥 Hapus Baris Terpilih", type="secondary", use_container_width=True):
          st.session_state["konfirmasi_hapus"] = True
          st.session_state["target_hapus"] = "Row"
          st.session_state["val_hapus_row"] = id_hapus_pilihan
      else:
        if st.button("🔥 Hapus Data", type="secondary", use_container_width=True):
          st.session_state["konfirmasi_hapus"] = True
          st.session_state["target_hapus"] = opsi_hapus

    if st.session_state.get("konfirmasi_hapus", False):
      if st.session_state["target_hapus"] == "Row":
        st.warning(f"⚠️ Anda akan menghapus data dengan **ID #{st.session_state['val_hapus_row']}** secara permanen.")
      else:
        st.warning(
            "⚠️ Anda akan menghapus data kategori:"
            f" **{st.session_state['target_hapus']}** secara permanen."
        )
      
      password_admin = st.text_input(
          "Masukkan Password Konfirmasi Hapus:", type="password"
      )
      c1, c2 = st.columns(2)
      with c1:
        if st.button("❌ Batal"):
          st.session_state["konfirmasi_hapus"] = False
          st.rerun()
      with c2:
        if st.button("✅ Ya, Hapus Permanen", type="primary"):
          if password_admin == "admin123":
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            if st.session_state["target_hapus"] == "Row":
              cursor.execute("DELETE FROM kanvas WHERE id = ?", (st.session_state["val_hapus_row"],))
            elif st.session_state["target_hapus"] == "Hari Ini":
              cursor.execute("DELETE FROM kanvas WHERE tanggal = ?", (hari_ini,))
            else:
              cursor.execute("DELETE FROM kanvas")
            conn.commit()
            conn.close()
            st.session_state.pop("konfirmasi_hapus", None)
            st.session_state["notifikasi_sukses"] = "🗑️ Data berhasil dihapus."
            st.rerun()
          else:
            st.error("❌ Password salah!")
  else:
    st.info("📭 Belum ada data laporan kanvas yang tercatat.")

  # ====================================================
  # MODUL REKAPITULASI HARIAN & MINGGUAN
  # ====================================================
  st.markdown("---")
  st.markdown("### 📈 Rekapitulasi Harian & Mingguan (Report Table)")

  df_rekap_data = muat_data()
  if not df_rekap_data.empty:
    df_rekap_data["Tanggal_DT"] = pd.to_datetime(df_rekap_data["Tanggal"])

    col_rk1, col_rk2, col_rk3, col_rk4 = st.columns(4)

    with col_rk1:
      daftar_zona_pilihan = ["Semua Zona"] + sorted(
          list(set(PROMOTOR_ZONA.values()))
      )
      pilih_zona = st.selectbox(
          "Pilih Zona", daftar_zona_pilihan, key="rekap_zona"
      )

    with col_rk2:
      daftar_brand_pilihan = ["Semua Brand"] + DAFTAR_BRAND
      pilih_brand = st.selectbox(
          "Pilih Brand", daftar_brand_pilihan, key="rekap_brand"
      )

    if pilih_zona != "Semua Zona":
      df_filtered_zona = df_rekap_data[df_rekap_data["Zona"] == pilih_zona]
    else:
      df_filtered_zona = df_rekap_data.copy()

    if pilih_brand != "Semua Brand":
      df_filtered_brand = df_filtered_zona[
          df_filtered_zona["Brand"] == pilih_brand
      ]
    else:
      df_filtered_brand = df_filtered_zona.copy()

    with col_rk3:
      pilih_tahun = st.selectbox(
          "Pilih Tahun",
          sorted(
              df_filtered_brand["Tanggal_DT"].dt.year.unique(), reverse=True
          ),
          key="rekap_thn",
      )

    with col_rk4:
      df_filtered_tahun = df_filtered_brand[
          df_filtered_brand["Tanggal_DT"].dt.year == pilih_tahun
      ]
      list_minggu = sorted(
          df_filtered_tahun["Tanggal_DT"].dt.isocalendar().week.unique(),
          reverse=True,
      )
      pilih_minggu = st.selectbox(
          "Pilih Minggu ke- (Week)", list_minggu, key="rekap_mg"
      )

    df_mingguan = df_filtered_tahun[
        df_filtered_tahun["Tanggal_DT"].dt.isocalendar().week == pilih_minggu
    ]

    if not df_mingguan.empty:
      mapping_hari = {0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis", 4: "Jumat"}
      df_mingguan["Nama Hari"] = df_mingguan["Tanggal_DT"].dt.weekday.map(
          mapping_hari
      )
      daftar_hari_kolom = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat"]
      rekap_harian_dict = {}

      for hari in daftar_hari_kolom:
        df_hari = df_mingguan[df_mingguan["Nama Hari"] == hari]
        if not df_hari.empty:
          tgl_str = df_hari["Tanggal"].iloc[0]
          tgl_formatted = datetime.strptime(tgl_str, "%Y-%m-%d").strftime(
              "%d/%m/%Y"
          )
          total_armada = df_hari["Nama Promotor"].nunique()
          beli_ada = df_hari["Outlet Beli Ada"].sum()
          beli_ks_tb = df_hari["Outlet Ks Tb"].sum()
          beli_ks_b = df_hari["Outlet Ks B"].sum()
          tba_aktif = df_hari["Outlet TB Ada A"].sum()
          tba_pasif = df_hari["Outlet TB Ada P"].sum()
          kosong = df_hari["Outlet TB Ks"].sum()
          outlet_buka_ecer = df_hari["Outlet Buka Ecer"].sum()
          call = (
              beli_ada + beli_ks_tb + beli_ks_b + tba_aktif + tba_pasif + kosong
          )
          total_omset = df_hari["Omset (Bungkus)"].sum()
          total_setoran = df_hari["Jumlah Setoran (Rp)"].sum()
          total_outlet_beli = beli_ada + beli_ks_tb + beli_ks_b
          avg_dropsize = (
              round(total_omset / total_outlet_beli, 1)
              if total_outlet_beli > 0
              else 0.0
          )
          ec = beli_ada + beli_ks_tb + beli_ks_b
          persen_ec = round((ec / call) * 100, 1) if call > 0 else 0.0
          avail_sebelum = (
              round(((beli_ada + tba_aktif + tba_pasif) / call) * 100, 1)
              if call > 0
              else 0.0
          )
          avail_sesudah = (
              round(
                  (
                      (
                          beli_ada
                          + beli_ks_tb
                          + beli_ks_b
                          + tba_aktif
                          + tba_pasif
                      )
                      / call
                  )
                  * 100,
                  1,
              )
              if call > 0
              else 0.0
          )
          persen_repeat = (
              round(
                  (
                      (beli_ada + beli_ks_tb)
                      / (beli_ada + beli_ks_tb + tba_aktif + tba_pasif)
                  )
                  * 100,
                  1,
              )
              if (beli_ada + beli_ks_tb + tba_aktif + tba_pasif) > 0
              else 0.0
          )
          persen_oos = (
              round((beli_ks_tb / call) * 100, 1) if call > 0 else 0.0
          )
          persen_ecer = (
              round((outlet_buka_ecer / call) * 100, 1) if call > 0 else 0.0
          )

          rekap_harian_dict[hari] = {
              "Tanggal": tgl_formatted,
              "Total Armada": total_armada,
              "Call": call,
              "Beli Ada": beli_ada,
              "Beli Ks Tambah": beli_ks_tb,
              "Beli Ks Baru": beli_ks_b,
              "TBA Aktif": tba_aktif,
              "TBA Pasif": tba_pasif,
              "Kosong": kosong,
              "Total Omset": total_omset,
              "Jumlah Setoran (Rp)": total_setoran,
              "Average Dropsize": avg_dropsize,
              "% Availability Sebelum": f"{avail_sebelum}%",
              "% Availability Sesudah": f"{avail_sesudah}%",
              "EC": ec,
              "% EC": f"{persen_ec}%",
              "% Repeat": f"{persen_repeat}%",
              "% OOS": f"{persen_oos}%",
              "% Outlet Ecer": f"{persen_ecer}%",
              "Total Sampling": df_hari["Jumlah Rokok Sampling"].sum(),
              "Kontak Konsumen": df_hari["Jumlah Konsumen Trial"].sum(),
              "Laku Direct Selling": df_hari["Direct Selling"].sum(),
          }
        else:
          rekap_harian_dict[hari] = {
              "Tanggal": "-",
              "Total Armada": 0,
              "Call": 0,
              "Beli Ada": 0,
              "Beli Ks Tambah": 0,
              "Beli Ks Baru": 0,
              "TBA Aktif": 0,
              "TBA Pasif": 0,
              "Kosong": 0,
              "Total Omset": 0,
              "Jumlah Setoran (Rp)": 0,
              "Average Dropsize": 0.0,
              "% Availability Sebelum": "0.0%",
              "% Availability Sesudah": "0.0%",
              "EC": 0,
              "% EC": "0.0%",
              "% Repeat": "0.0%",
              "% OOS": "0.0%",
              "% Outlet Ecer": "0.0%",
              "Total Sampling": 0,
              "Kontak Konsumen": 0,
              "Laku Direct Selling": 0,
          }

      df_final_rekap = pd.DataFrame(rekap_harian_dict)
      label_zona_judul = (
          f"Zona {pilih_zona}" if pilih_zona != "Semua Zona" else "Semua Zona"
      )
      label_brand_judul = (
          f" - {pilih_brand}" if pilih_brand != "Semua Brand" else ""
      )

      st.markdown(
          f"#### Laporan Rekapitulasi {label_zona_judul}{label_brand_judul} -"
          f" Minggu ke {pilih_minggu} - {pilih_tahun}"
      )

      if os.path.exists("76aksara.png"):
        st.image("76aksara.png", use_container_width=True)

      st.table(df_final_rekap)

      st.markdown("#### 📥 Unduh Rekap Laporan sebagai Gambar")
      judul_rekap = (
          f"Laporan Rekapitulasi {label_zona_judul}{label_brand_judul} -"
          f" Minggu ke {pilih_minggu} - {pilih_tahun}"
      )

      try:
        img_buffer = buat_gambar_rekap(df_final_rekap, judul_rekap)

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
          st.download_button(
              label="📷 Download PNG",
              data=img_buffer.getvalue(),
              file_name=(
                  f"rekap_kanvas_{pilih_zona.replace(' ', '_')}"
                  f"_{pilih_brand.replace(' ', '_')}_minggu{pilih_minggu}_{pilih_tahun}.png"
              ),
              mime="image/png",
              use_container_width=True,
              key="dl_rekap_png",
          )
        with col_dl2:
          img_buffer.seek(0)
          pil_img = PILImage.open(img_buffer).convert("RGB")
          jpeg_buf = BytesIO()
          pil_img.save(jpeg_buf, format="JPEG", quality=95)
          jpeg_buf.seek(0)

          st.download_button(
              label="🖼️ Download JPEG",
              data=jpeg_buf.getvalue(),
              file_name=(
                  f"rekap_kanvas_{pilih_zona.replace(' ', '_')}"
                  f"_{pilih_brand.replace(' ', '_')}_minggu{pilih_minggu}_{pilih_tahun}.jpg"
              ),
              mime="image/jpeg",
              use_container_width=True,
              key="dl_rekap_jpeg",
          )
      except Exception as e:
        st.warning(f"Gagal membuat gambar rekap: {e}")
    else:
      st.info(
          f"📭 Tidak ada data laporan untuk {pilih_zona} dan brand {pilih_brand}"
          f" pada Minggu ke-{pilih_minggu}."
      )
  else:
    st.info("📭 Belum ada data untuk direkap.")

  # ====================================================
  # TOMBOL BACKUP MANUAL KE GOOGLE SHEETS
  # ====================================================
  st.markdown("---")
  st.markdown("### ☁️ Backup Data ke Google Sheets")
  st.markdown(
      "Gunakan tombol di bawah ini jika Anda ingin melakukan sinkronisasi atau"
      " backup ulang seluruh data lokal ke Google Sheets secara manual."
  )

  if st.button("🔄 Kirim/Backup Semua Data ke Google Sheets", type="primary"):
    df_lokal = muat_data()

    if not df_lokal.empty:
      progress_bar = st.progress(0)
      total_data = len(df_lokal)
      sukses = 0

      for i, row in df_lokal.iterrows():
        val_setoran_bk = (
            int(row["Jumlah Setoran (Rp)"])
            if "Jumlah Setoran (Rp)" in row and pd.notnull(row["Jumlah Setoran (Rp)"])
            else 0
        )
        payload_manual = {
            "id": int(row["ID"]),
            "tanggal": str(row["Tanggal"]),
            "nama_promotor": str(row["Nama Promotor"]),
            "zona": str(row["Zona"]),
            "brand": str(row["Brand"]),
            "canvas_plan": int(row["Canvas Plan"]),
            "outlet_beli_ada": int(row["Outlet Beli Ada"]),
            "outlet_ks_tb": int(row["Outlet Ks Tb"]),
            "outlet_ks_b": int(row["Outlet Ks B"]),
            "outlet_tb_ada_a": int(row["Outlet TB Ada A"]),
            "outlet_tb_ada_p": int(row["Outlet TB Ada P"]),
            "outlet_tb_ks": int(row["Outlet TB Ks"]),
            "omset_bungkus": int(row["Omset (Bungkus)"]),
            "promsus_10_1": int(row["Promsus 10+1"]),
            "promsus_3_1": int(row["Promsus 3+1"]),
            "promsus_2_1": int(row["Promsus 2+1"]),
            "promsus_1_1": int(row["Promsus 1+1"]),
            "promsus_n_mie_instan": int(row["N+ Mie Instan"]),
            "outlet_buka_ecer": int(row["Outlet Buka Ecer"]),
            "jumlah_rokok_sampling": int(row["Jumlah Rokok Sampling"]),
            "jumlah_konsumen_trial": int(row["Jumlah Konsumen Trial"]),
            "direct_selling": int(row["Direct Selling"]),
            "jumlah_setoran": val_setoran_bk,
            "waktu_submit": str(row["Waktu Submit"]),
        }

        try:
          response = requests.post(WEBHOOK_URL, json=payload_manual, timeout=10)
          if response.status_code == 200:
            sukses += 1
        except Exception:
          pass

        progress_bar.progress((i + 1) / total_data)

      st.success(
          f"✅ Berhasil mem-backup {sukses} dari {total_data} data ke Google"
          " Sheets!"
      )
    else:
      st.info("📭 Belum ada data di database lokal untuk di-backup.")
