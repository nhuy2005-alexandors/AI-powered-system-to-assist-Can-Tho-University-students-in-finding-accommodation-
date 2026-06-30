# -*- coding: utf-8 -*-
"""Generate PDF Use Case Specification using fpdf2 (pure Python, no system deps)."""
from fpdf import FPDF
import os

class UCSpecPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, "THS2026-66 | He thong Tong hop & Goi y Nha tro AI", align="C")
        self.ln(6)
        self.set_draw_color(21, 101, 192)
        self.line(10, self.get_y(), self.w - 10, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Trang {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title, color=(46, 125, 50)):
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(*color)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def uc_table(self, rows, col_widths, headers):
        self.set_font("Helvetica", "B", 7)
        self.set_fill_color(21, 101, 192)
        self.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 6, h, border=1, fill=True, align="C")
        self.ln()

        self.set_font("Helvetica", "", 7)
        self.set_text_color(30, 30, 30)

        for row_idx, row in enumerate(rows):
            fill = row_idx % 2 == 0
            if fill:
                self.set_fill_color(245, 248, 255)
            else:
                self.set_fill_color(255, 255, 255)

            # Calculate max height needed
            max_lines = 1
            for i, cell_text in enumerate(row):
                lines = self.multi_cell(col_widths[i], 4, cell_text, dry_run=True, output="LINES")
                max_lines = max(max_lines, len(lines))

            cell_h = max(max_lines * 4, 6)
            x_start = self.get_x()
            y_start = self.get_y()

            # Check page break
            if y_start + cell_h > self.h - 20:
                self.add_page()
                # Re-draw header
                self.set_font("Helvetica", "B", 7)
                self.set_fill_color(21, 101, 192)
                self.set_text_color(255, 255, 255)
                for i, h in enumerate(headers):
                    self.cell(col_widths[i], 6, h, border=1, fill=True, align="C")
                self.ln()
                self.set_font("Helvetica", "", 7)
                self.set_text_color(30, 30, 30)
                y_start = self.get_y()
                if fill:
                    self.set_fill_color(245, 248, 255)
                else:
                    self.set_fill_color(255, 255, 255)

            for i, cell_text in enumerate(row):
                x = x_start + sum(col_widths[:i])
                self.set_xy(x, y_start)
                # Draw background rect
                self.rect(x, y_start, col_widths[i], cell_h, style="DF" if fill else "D")
                self.set_xy(x + 0.5, y_start + 0.5)
                if i == 0:  # ID column - bold blue
                    self.set_font("Helvetica", "B", 7)
                    self.set_text_color(21, 101, 192)
                else:
                    self.set_font("Helvetica", "", 7)
                    self.set_text_color(30, 30, 30)
                self.multi_cell(col_widths[i] - 1, 4, cell_text)

            self.set_xy(x_start, y_start + cell_h)


def main():
    pdf = UCSpecPDF(orientation="L", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(21, 101, 192)
    pdf.cell(0, 10, "DAC TA USE CASE", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, "He thong Tong hop & Goi y Nha tro Ung dung AI - THS2026-66", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "Phien ban 1.0 - Ngay: 10/06/2026", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Note box
    pdf.set_fill_color(255, 253, 231)
    pdf.set_draw_color(249, 168, 37)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(50, 50, 50)
    pdf.rect(10, pdf.get_y(), pdf.w - 20, 12, style="DF")
    pdf.set_x(14)
    pdf.cell(0, 6, "Pham vi: He thong hoat dong theo mo hinh Aggregator. Du lieu o muc gan real-time (6-12h).")
    pdf.ln(5)
    pdf.set_x(14)
    pdf.cell(0, 6, "Xac nhan phong con trong nam ngoai pham vi - nguoi dung tu xac nhan qua link nguon goc.")
    pdf.ln(10)

    headers = ["ID", "Ten UC", "Actor", "Mo ta", "Dieu kien tien quyet", "Luong chinh", "Luong thay the", "Dieu kien sau"]
    col_widths = [18, 25, 18, 30, 25, 68, 55, 38]

    # === NHOM A ===
    pdf.section_title("NHOM A - NEN TANG WEB CO BAN", (21, 101, 192))
    rows_a = [
        ["UC-A1.1", "Dang ky tai khoan", "Guest", "Tao TK bang Email+MK, xac thuc OTP.", "Email chua ton tai.", "1.Bam Dang ky 2.Dien form 3.Validate 4.Gui OTP email 5.Nhap OTP 6.Tao TK -> Onboarding", "Email da co->Bao loi. MK yeu->Loi. OTP sai->3 lan. OTP het han->Gui lai.", "TK tao (role=user), chuyen Onboarding"],
        ["UC-A1.2", "Dang nhap", "Guest", "Dang nhap Email/Password, nhan JWT.", "Da co TK.", "1.Bam Dang nhap 2.Nhap Email+MK 3.JWT Access(15p)+Refresh(7d) 4.Chuyen trang chu", "Sai MK->'Email hoac MK khong dung'. >5 lan->Khoa 15p.", "JWT luu httpOnly cookie"],
        ["UC-A1.3", "Dang nhap Google", "Guest", "OAuth 2.0 one-click. Tu tao TK neu chua co.", "Khong.", "1.Bam 'Google' 2.Redirect Consent 3.Cap quyen 4.Auth Code 5.ID Token 6a.Moi->Tao TK 6b.Cu->Login 7.JWT", "Tu choi cap quyen->Quay lai login.", "Dang nhap OK. TK moi->Quiz"],
        ["UC-A1.4", "Quen mat khau", "Guest", "Gui link dat lai MK qua email.", "Da co TK.", "1.Bam Quen MK 2.Nhap email 3.Gui link reset(30p) 4.Mo link, nhap MK moi 5.Cap nhat hash", "Email khong co->Van hien 'Da gui'. Link het han->Gui lai.", "MK doi thanh cong"],
        ["UC-A2.1", "Tim kiem nha tro", "Guest/User", "Tim text + Loc da tieu chi + Sap xep + Ban do.", "Khong (khong can dang nhap).", "1.Nhap tu khoa 2.Ket qua+sidebar loc 3.Loc: Gia(slider),DT,Quan,Tien ich(checkbox),KC CTU 4.Sap xep 5.20 tin/trang 6.List/Map View", "Khong nhap->Hien tat ca. Map View: Pin Leaflet/OSM, click->popup.", "DS ket qua + badge rui ro + timestamp"],
        ["UC-A2.5", "Tim theo ban kinh", "Guest/User", "Ve vong tron tren ban do, chi hien phong trong BK.", "Dang o Map View.", "1.Click 1 diem(hoac CTU) 2.Slider ban kinh(500m-5km) 3.PostGIS:ST_DWithin 4.Chi hien trong vong tron", "-", "Ket qua loc theo khong gian"],
        ["UC-A3.1", "Xem chi tiet", "Guest/User", "Trang chi tiet: anh, gia, ban do, risk, nguon goc.", "Khong.", "1.Click 1 tin 2.Hien: Gallery, Gia, DT, Tien ich, Ban do+POI, Badge rui ro, Nguon+link, 'Cap nhat X ngay truoc' 3.Disclaimer", "-", "Extend: Luu, Bao cao, Chia se"],
        ["UC-A3.2", "Luu yeu thich", "User", "Bookmark phong tro.", "Da dang nhap.", "1.Bam heart 2.Luu vao favorites 3.Icon doi thanh filled 4.Bam lai->Bo", "Chua login->Popup 'Dang nhap de luu'.", "Tin them/xoa khoi yeu thich"],
        ["UC-A3.3", "So sanh phong tro", "User", "So sanh side-by-side 2-3 phong.", "Da dang nhap.", "1.'Them vao so sanh'(2-3 tin) 2.'So sanh ngay' 3.Bang: Gia,DT,Tien ich,KC CTU,KC CA,Risk", ">3 tin->Bao loi 'Toi da 3 phong'.", "Bang so sanh hien thi"],
        ["UC-A3.5", "Bao cao tin sai", "User", "Bao cao tin sai/lua dao.", "Da dang nhap.", "1.Bam 'Bao cao' 2.Chon ly do 3.Ghi chu(tuy chon) 4.Luu reports(pending) 5.Admin nhan TB", "-", "Report ghi nhan, Admin duyet"],
        ["UC-A4.1", "Dang tin UGC", "User", "SV tu dang tin moi.", "Da dang nhap.", "1.'Dang tin' 2.Dien form(Tieu de,Gia,DT,Dia chi,Anh<=10,Mo ta,Tien ich) 3.'Dang' 4.AI Risk Check 5a.Risk thap->Dang ngay 5b.Risk cao->Cho Admin", "Thieu truong->Loi. Anh>5MB->Nen lai.", "Tin dang hoac cho duyet"],
        ["UC-A5.1", "Thong bao tin moi", "User", "Push khi co tin khop tieu chi.", "Da login, co preference_vector.", "1.Crawler tim tin moi 2.So khop preference vector 3.Cosine>nguong->Push/Email 4.Noi dung: Tieu de,Gia,Khu vuc", "-", "User nhan TB, click->chi tiet"],
    ]
    pdf.uc_table(rows_a, col_widths, headers)

    # === NHOM B ===
    pdf.add_page()
    pdf.section_title("NHOM B - TINH NANG AI", (46, 125, 50))
    rows_b = [
        ["UC-B1.1", "Onboarding Quiz", "User", "3 cau hoi nhanh tao preference vector.", "Vua dang ky / chua dien.", "1.Hien 3 cau: Q1:Ngan sach?(Slider 500K-5M) Q2:KC max CTU?(500m-5km) Q3:Tien ich bat buoc?(Checkbox) 2.'Hoan tat' 3.Chuyen->preference_vector", "'Bo qua'->Dung Popularity-Based.", "User co vector, AI Recommendation hoat dong"],
        ["UC-B1.2", "Goi y 'Danh cho ban'", "User", "Top-10 phong phu hop nhat trang chu.", "Da login, co preference_vector.", "1.Mo trang chu 2.Lay preference_vector 3.Cosine Similarity vs tat ca listing(active) 4.Top-10->'Danh cho ban'", "Chua co vector->'Top pho bien tuan nay'.", "Goi y ca nhan. Extend: Tab 'Kham pha'(80/20)"],
        ["UC-B1.3", "Implicit Feedback", "System", "Thu thap hanh vi an cap nhat vector.", "User dang duyet tin.", "1.Ghi nhan: thoi gian xem(>30s), bookmark, click link, click SDT 2.Luu user_interactions 3.Dinh ky cap nhat preference_vector", "-", "Vector nguoi dung ngay cang chinh xac"],
        ["UC-B2.1", "Tim ban o ghep", "User", "Matching ban ghep (Forced Choice Survey).", "Da login + Da dien ho so.", "1.'Tim ban ghep' 2.Chua co->Dien form tinh huong(6 cau) 3.Weighted Cosine Similarity 4.Loc Score>=0.7 5.Hien: Avatar,Ten,Score(%),Tom tat 6.'Gui loi moi'", "Khong ai>=0.7->'Chua co ban phu hop, se TB khi co nguoi moi'.", "DS ban ghep / Loi moi gui"],
        ["UC-B3.1", "Chatbot AI (RAG)", "User", "Hoi ngon ngu tu nhien, tra loi tu du lieu thuc.", "Da login. Vector DB da index.", "1.Mo chatbot 2.Nhap cau hoi 3.Nhung->Vector(e5-small) 4.pgvector:Top-5+score 5a.Score>=0.65->Prompt(context+POI)->Gemini->Tra loi+link 5b.Score<0.65->'Khong tim thay' 6.Luu Memory(5 luot)", "Cau hoi ngoai domain->'Toi chi ho tro tim nha tro.'", "Tra loi + nguon. Memory cap nhat multi-turn"],
        ["UC-B4.1", "Badge canh bao rui ro", "Guest/User", "Badge rui ro AI tinh tu dong tren moi tin.", "Khong.", "1.Hien badge: An toan(risk<0.3) / Can kiem chung(0.3-0.6) / Nghi van(>=0.6) 2.Click->Popup ly do: 'Gia thap 40%', 'Khong co anh'...", "-", "Nguoi dung biet muc tin cay"],
    ]
    pdf.uc_table(rows_b, col_widths, headers)

    # === NHOM C ===
    pdf.add_page()
    pdf.section_title("NHOM C - HE THONG & ADMIN", (230, 81, 0))
    rows_c = [
        ["UC-C1.1", "Crawl tu dong", "System", "Crawler dinh ky 6-12h lay du lieu.", "Cron job cau hinh.", "1.Cron trigger(6h) 2.Doc nguon+CSS selectors(JSON) 3.HTTP(1req/5s,xoay UA) 4.Parse HTML 5.NLP trich xuat 6.Geocoding 7.MinHash+LSH dedup 8.PostGIS POI 9.AI Risk 10.Nhung vector 11.INSERT/UPDATE", "Bi block(403)->Log,alert,bo qua. HTML doi->Parser null->Log.", "DB cap nhat. <10 tin moi->Canh bao"],
        ["UC-C1.2", "Chuan hoa NLP & Geocoding", "System", "Trich xuat tien ich + dia chi->GPS.", "Co du lieu tho tu crawler.", "1.NLP parse mo ta->JSONB tien ich 2.Geocoding: Google API->Landmark->Phuong fallback 3.Luu geocode_confidence", "Geocode fail->confidence='failed', an khoi ban do.", "Du lieu chuan hoa + co toa do"],
        ["UC-C1.5", "Tinh khoang cach POI", "System", "PostGIS tinh KC den don CA, BV, bus.", "Phong co toa do + poi_locations da seed.", "1.Voi moi tin moi(co lat/lng) 2.PostGIS:ST_DistanceSphere()->distance_to_police,hospital 3.Cap nhat aggregated_listings", "Tin khong co toa do->Bo qua, NULL.", "Cac cot distance_to_* duoc dien"],
        ["UC-C2.1", "Dashboard tong quan", "Admin", "Thong ke tong quan he thong.", "Dang nhap Admin.", "1.Truy cap /admin 2.Hien: Tong tin(active/stale), Tin moi hom nay, Tin bi report, Crawler status, So user, Top phong", "-", "Dashboard hien thi"],
        ["UC-C2.2", "Kiem duyet tin flagged", "Admin", "Duyet/An/Xoa tin bi canh bao.", "Co tin trong hang cho.", "1.Xem DS: risk cao + bi report 2.Moi tin: Noi dung, Ly do, So report, Risk reasons 3.Chon: Duyet/An/Xoa vinh vien", "-", "Tin duoc xu ly, trang thai cap nhat"],
        ["UC-C2.3", "Cau hinh Crawler", "Admin", "Bat/tat nguon, doi tan suat, xem log.", "Dang nhap Admin.", "1.Truy cap 'Cau hinh Crawler' 2.DS nguon: Bat/Tat toggle, Tan suat(dropdown), Log gan nhat 3.'Luu cau hinh'", "-", "Config crawler cap nhat"],
    ]
    pdf.uc_table(rows_c, col_widths, headers)

    # === RELATIONSHIPS ===
    pdf.add_page()
    pdf.section_title("QUAN HE GIUA CAC USE CASE", (106, 27, 154))
    rel_headers = ["Quan he", "UC co so", "UC lien quan", "Giai thich"]
    rel_widths = [30, 50, 80, 117]
    rel_rows = [
        ["<<include>>", "UC-A2.1 (Tim kiem)", "UC-A2.2 (Loc), UC-A2.3 (Sap xep)", "Tim kiem luon bao gom bo loc va sap xep"],
        ["<<include>>", "UC-A3.1 (Chi tiet)", "UC-B4.1 (Badge rui ro)", "Trang chi tiet luon hien badge"],
        ["<<include>>", "UC-B1.2 (Goi y)", "UC-B1.1 (Onboarding)", "Goi y can onboarding quiz truoc"],
        ["<<include>>", "UC-B2.1 (Matching)", "UC-B2.1a (Ho so ghep)", "Matching can co ho so"],
        ["<<include>>", "UC-A4.1 (Dang tin)", "UC-B4 (Risk Check)", "Tin UGC luon qua AI kiem tra"],
        ["<<include>>", "UC-C1.1 (Crawl)", "UC-C1.2, C1.3, C1.5, C1.6", "Crawl bao gom toan bo pipeline"],
        ["<<extend>>", "UC-A3.1 (Chi tiet)", "UC-A3.2 (Yeu thich), UC-A3.5 (Bao cao), UC-A3.4 (Chia se)", "Hanh dong tuy chon tu trang chi tiet"],
        ["<<extend>>", "UC-B1.2 (Goi y)", "UC-B1.4 (Kham pha 80/20)", "Tab Explore la mo rong tuy chon"],
    ]
    pdf.uc_table(rel_rows, rel_widths, rel_headers)

    # Save
    out = r"d:\Dev\Workspaces\NCKH\Agent-Generated\DacTa_UseCase.pdf"
    pdf.output(out)
    print(f"PDF created: {out}")
    print(f"Size: {os.path.getsize(out) / 1024:.1f} KB")

if __name__ == "__main__":
    main()
