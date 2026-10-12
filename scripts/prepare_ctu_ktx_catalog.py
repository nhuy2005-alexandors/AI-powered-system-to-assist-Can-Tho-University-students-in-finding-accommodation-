"""Build the shared KTX catalogue without guessing fees, geography or aliases."""
from __future__ import annotations

import csv
import argparse
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data/student_housing"
OUT = ROOT / "apps/api/app/ktx/catalog.json"
FACILITIES = "https://ssc.ctu.edu.vn/hoat/160-cs1.html"
INTRO = "https://ssc.ctu.edu.vn/hoat/213-ktx25.html"
REGISTRATION = "https://ssc.ctu.edu.vn/images/upload/thong_bao/072026_tb_dk1_2627.pdf"
NEW_STUDENTS = "https://tansinhvien.ctu.edu.vn/sinh-hoat/huong-dan-tan-sinh-vien-dang-ky-o-ky-tuc-xa"
FEES = "https://tansinhvien.ctu.edu.vn/images/upload/Tansinhvien_K51/KTX/2025_Phieu_DK_KTX_TSV_F2.pdf"
RULES = "https://ssc.ctu.edu.vn/images/upload/Noiquy_KTX_trich_092025.pdf"


def point(osm, way_id):
    nodes = {n.attrib["id"]: (float(n.attrib["lat"]), float(n.attrib["lon"])) for n in osm.findall("node")}
    way = next(w for w in osm.findall("way") if w.attrib["id"] == str(way_id))
    coords = [nodes[n.attrib["ref"]] for n in way.findall("nd")]
    if coords[0] == coords[-1]:
        coords.pop()
    # Representative point of the mapped footprint, not an entrance coordinate.
    return dict(lat=round(sum(p[0] for p in coords) / len(coords), 7),
                lng=round(sum(p[1] for p in coords) / len(coords), 7),
                source_url=f"https://www.openstreetmap.org/way/{way_id}",
                source_name="OpenStreetMap contributors · ODbL 1.0", osm_type="way", osm_id=way_id,
                precision="representative", verified_at="2026-10-12")


def submitted_rows(path):
    text = path.read_text(encoding="utf-8-sig")
    lines = [line for line in text.splitlines() if line.strip()]
    # Accept both normal CSV and the user's mixed free-text/CSV revision.
    if len(lines) > 1 and not lines[1].startswith('"'):
        old = next((i for i, line in enumerate(lines[1:], 1) if line.startswith('"')), len(lines))
        records = []
        for line in lines[1:old]:
            code = re.match(r"^(\w+)\s+", line)
            capacity = re.search(r"sức chứa\s*(\d+)", line, re.I) or re.search(r"phòng\s*(\d+)\s*người", line, re.I)
            price = re.search(r"(\d+(?:[.,]\d+)?)\s*k\s*/", line, re.I)
            if not all((code, capacity, price)):
                raise ValueError("Cannot parse updated room row: " + line)
            desc = line[code.end():price.start()].strip(" ,")
            desc = re.sub(r"sức chứa\s*\d+\s*(?:người)?", "", desc, flags=re.I).strip(" ,")
            desc = desc.replace("đc phép", "được phép").replace("nvs", "nhà vệ sinh")
            records.append({"Loại phòng": code[1], "Có gì": desc, "Sức chứa": capacity[1] + " người",
                            "Đơn giá (VND)": int(float(price[1].replace(",", ".")) * 1000)})
        records += list(csv.DictReader(io.StringIO("\n".join([lines[0], *lines[old:]]))))
    else:
        records = list(csv.DictReader(io.StringIO(text)))
    rooms = []
    for row in records:
        code, desc, capacity = row["Loại phòng"].strip(), row["Có gì"].strip(), row["Sức chứa"].strip()
        price = int(str(row.get("Đơn giá (VND)", row.get("Giá (VND/người)", ""))).replace(".", "").replace(",", ""))
        cooking = False if "không được nấu" in desc else True if "nấu ăn" in desc else None
        rooms.append(dict(id="submitted-" + code.lower(), code=code,
            area_ids=["A"] if re.fullmatch(r"A\d*", code) else [],
            capacities=[int(n) for n in re.findall(r"\d+", capacity)], capacity_label=capacity,
            cooking_allowed=cooking, bed_type="bunk" if "giường tầng" in desc else "single" if "giường bộ" in desc else "unknown",
            bathroom="Nhà vệ sinh tập thể trong khuôn viên dãy" if code == "A4" else None,
            description=desc, price=price, price_period="unconfirmed", source_id="submitted",
            notes="Đơn giá/người theo danh mục cập nhật; chưa xác nhận kỳ tính giá và thời hạn áp dụng."))
    return rooms


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DATA / "ktx_ctu_loai_phong_cap_nhat.csv")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "apps/web/public/images/ktx/sources.json").read_text(encoding="utf-8"))
    osm = ET.parse(DATA / "sources/ctu-khu-ii-openstreetmap.osm").getroot()
    gps_a, gps_b = point(osm, 89864434), point(osm, 168528554)
    gps_a["label"] = "Văn phòng phục vụ sinh viên KTX khu A"
    gps_b["label"] = "Điểm đại diện KTX khu B"
    sources = [
        dict(id="submitted", title="Danh mục loại phòng do người dùng cập nhật", url=None, year=None, note="Kỳ tính đơn giá chưa được xác nhận."),
        dict(id="ctu_2025", title="Phiếu đăng ký KTX khóa mới · tài liệu CTU 2025", url=FEES, year=2025, note="Phí/người/học kỳ 3,5 tháng. Dữ liệu tham khảo lịch sử, chưa xác nhận cho 2026–2027."),
        dict(id="facilities", title="Cơ sở vật chất KTX · Trung tâm Phục vụ Sinh viên", url=FACILITIES, year=None, note="Trang giới thiệu không ghi ngày áp dụng biểu phí."),
        dict(id="intro", title="Giới thiệu KTX Đại học Cần Thơ", url=INTRO, year=None, note="Quy mô theo bài giới thiệu."),
        dict(id="registration", title="Thông báo 307/TB-CTSV · HKI 2026–2027", url=REGISTRATION, year=2026, note="Ban hành 21/07/2026."),
        dict(id="new_students", title="Hướng dẫn tân sinh viên đăng ký KTX · 2026–2027", url=NEW_STUDENTS, year=2026, note="Học kỳ I 2026–2027."),
        dict(id="rules", title="Nội quy KTX · bản công khai CTU", url=RULES, year=None, note="Bản trích nội quy được CTU công bố."),
    ]
    input_path = args.input if args.input.exists() else ROOT / "tmp/ktx_loai_phong_tom_tat.csv"
    rooms = submitted_rows(input_path)
    # Keep a normal, editable CSV for subsequent updates; preserve the supplied file.
    with (DATA / "ktx_ctu_loai_phong_cap_nhat.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Loại phòng", "Có gì", "Sức chứa", "Đơn giá (VND)"])
        writer.writerows((room["code"], room["description"], room["capacity_label"], room["price"]) for room in rooms)
    with (DATA / "ktx_ctu_khu_a_b_loai_phong_phi_tham_khao.csv").open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            area, cap = row["Khu"], int(row["Suc_chua_SV"])
            cook, bed = row["Cho_nau_an"] == "Có", "bunk" if row["Giuong"] == "Giường tầng" else "single"
            code = f"{area} · {cap} người · " + ("nấu ăn" if cook else "không nấu ăn") + " · " + row["Giuong"].lower()
            rooms.append(dict(id=f"reference-{area.lower()}-{cap}-{int(cook)}-{bed}", code=code, area_ids=[area],
                capacities=[cap], capacity_label=f"{cap} người", cooking_allowed=cook, bed_type=bed,
                bathroom="WC và khu nấu ăn dùng chung cả dãy" if area == "A" and cap == 4 and cook else None,
                description=row["Ghi_chu"] or ("Được nấu ăn" if cook else "Không được nấu ăn, được dùng ấm đun siêu tốc"),
                price=int(row["Don_gia_VND_moi_SV_hoc_ky"]), price_period="semester_3_5_months", source_id="ctu_2025",
                notes="Theo phiếu đăng ký CTU năm 2025; chưa xác nhận mức thu 2026–2027."))
    facts_data = [
        ("location", "Vị trí", "KTX khu A và khu B nằm trong Khu II, Đại học Cần Thơ, đường 3/2, phường Ninh Kiều, thành phố Cần Thơ.", "facilities", ["location", "overview"]),
        ("capacity-a", "Quy mô khu A", "Khu A có khả năng bố trí khoảng 4.000 sinh viên; gồm 2 dãy 5 tầng, 12 dãy 2 tầng và 15 dãy 1 tầng theo trang giới thiệu CTU.", "intro", ["overview", "area_a"]),
        ("capacity-b", "Quy mô khu B", "Khu B gồm 8 dãy 5 tầng; mỗi dãy được thiết kế 78 phòng, tối đa 8 sinh viên/phòng. Tổng sức chứa được công bố khoảng 4.500 sinh viên.", "intro", ["overview", "area_b"]),
        ("cooking", "Nấu ăn và loại giường", "Khu A có loại phòng được nấu ăn 3, 4, 5, 6 hoặc 8 người, dùng giường bộ hoặc giường tầng; sinh viên tự trang bị dụng cụ. Phòng không nấu ăn có ở cả A và B, chỉ được dùng ấm đun siêu tốc. Mã PB trong danh mục là mã loại phòng, không phải căn cứ xác định khu B.", "facilities", ["cooking", "bed", "overview"]),
        ("fees", "Phí ở và đơn vị giá", "Trang cơ sở vật chất CTU công bố khoảng 220.000–475.000 đồng/sinh viên/tháng, chưa gồm điện nước, đóng theo học kỳ. Trang không ghi ngày áp dụng. Phiếu đăng ký năm 2025 có phí/người/học kỳ 3,5 tháng. Các đơn giá trong danh mục người dùng cập nhật chưa xác nhận kỳ tính; không khẳng định là giá/tháng hay mức thu hiện hành.", "facilities", ["price"]),
        ("utilities", "Điện nước", "Sinh viên nộp phí điện, nước hàng tháng theo lượng sử dụng thực tế của phòng; phí ở chưa bao gồm điện nước.", "registration", ["utilities", "price"]),
        ("wifi", "Wi-Fi và tiện ích", "Phòng ở có Wi-Fi riêng từng phòng. Trong khuôn viên có căn tin, siêu thị mini; trang giới thiệu còn nêu nhà xe và khu vực giặt sấy.", "new_students", ["wifi", "amenities", "overview"]),
        ("security", "An ninh", "KTX có hàng rào, hệ thống camera an ninh và bảo vệ chuyên nghiệp. Nội quy yêu cầu sinh viên tự bảo quản tư trang cá nhân.", "facilities", ["security", "amenities"]),
        ("parking", "Gửi xe", "Xe đạp được miễn phí gửi xe. Trang hướng dẫn tân sinh viên 2026–2027 công bố xe máy/xe điện 25.000 đồng/sinh viên/tháng, nộp theo học kỳ.", "new_students", ["parking", "price"]),
        ("semester", "Thời gian HKI 2026–2027", "HKI năm học 2026–2027 ở từ 07/09/2026 đến 18/12/2026, tính 3,5 tháng. Các mốc đăng ký/thu phí tập trung tháng 8 trong thông báo đã qua; sinh viên mới có nhu cầu cần liên hệ KTX để xác nhận.", "registration", ["semester", "registration"]),
        ("registration", "Đăng ký ở", "Sinh viên đăng ký mới qua Hệ thống Quản lý KTX bằng tài khoản sinh viên, email ktx@ctu.edu.vn hoặc trực tiếp tại Văn phòng Trung tâm Phục vụ Sinh viên. Có thể ghi nguyện vọng và đăng ký nhóm; ưu tiên nhóm đủ số người bằng sức chứa phòng. Kết quả phụ thuộc sắp xếp chỗ của KTX.", "registration", ["registration"]),
        ("new-students", "Tân sinh viên", "Tân sinh viên chưa có tài khoản hệ thống có thể điền mẫu nhu cầu ở được liên kết trên trang hướng dẫn chính thức. Sinh viên có tài khoản làm theo hướng dẫn đăng ký KTX qua hệ thống.", "new_students", ["registration"]),
        ("refund", "Chuyển chỗ, trả chỗ và hoàn phí", "Sinh viên có thể xin chuyển chỗ theo hướng dẫn và chỗ phù hợp còn trống. Trả chỗ trước hạn không được hoàn phí, ngoại lệ trả trong vòng 7 ngày từ ngày được duyệt chỗ qua hệ thống và có lý do chính đáng. Cần đối chiếu quy định với văn phòng trước khi trả chỗ.", "registration", ["refund", "registration"]),
        ("contact", "Liên hệ", "Email KTX: ktx@ctu.edu.vn. Văn phòng khu A: 0292 3872 178; khu B: 0292 3872 275, theo thông báo 2026–2027. Một biểu mẫu cũ ghi số khu A khác; ưu tiên số trong thông báo mới.", "registration", ["contact"]),
        ("quiet", "Giờ nghỉ và sinh hoạt", "Nội quy công khai yêu cầu không gây ồn trong giờ nghỉ 12:00–13:00 và 23:00–05:00; không hút thuốc ở phòng/khu công cộng, không tổ chức uống rượu bia; chỉ được nấu ăn tại dãy khu A được thiết kế cho phép.", "rules", ["rules"]),
        ("availability", "Chỗ còn trống", "Danh mục loại phòng, hình ảnh và tọa độ khu KTX không xác nhận số chỗ còn trống. Phải xem tình trạng trên Hệ thống Quản lý KTX hoặc liên hệ văn phòng để xác nhận tại thời điểm đăng ký.", "registration", ["availability"]),
    ]
    facts = [dict(id=i, title=t, content=c, source_id=s, tags=tags) for i, t, c, s, tags in facts_data]
    dormitories = [
        dict(id="A", name="Ký túc xá khu A", capacity=4000, description="Nhiều lựa chọn sức chứa; có loại phòng được nấu ăn, giường bộ và giường tầng.",
             buildings="2 dãy 5 tầng · 12 dãy 2 tầng · 15 dãy 1 tầng", phone="0292 3872 178", location=gps_a,
             cover="/images/ktx/khu-a.jpg"),
        dict(id="B", name="Ký túc xá khu B", capacity=4500, description="8 dãy nhà 5 tầng; phòng giường tầng. Phiếu đăng ký 2025 liệt kê bố trí 4–8 người.",
             buildings="8 dãy 5 tầng · thiết kế 78 phòng/dãy", phone="0292 3872 275", location=gps_b,
             cover="/images/ktx/khu-b.jpg"),
    ]
    catalog = dict(version="ctu-ktx-2026-10-12", updated_at="2026-10-12", email="ktx@ctu.edu.vn",
                   address="Khu II, Đại học Cần Thơ, đường 3/2, phường Ninh Kiều, Cần Thơ",
                   registration_url=NEW_STUDENTS, sources=sources, dormitories=dormitories, room_types=rooms,
                   facts=facts, images=manifest["images"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(rooms=len(rooms), images=len(catalog["images"]), dormitories=2, facts=len(facts),
                         sha256=hashlib.sha256(OUT.read_bytes()).hexdigest())))


if __name__ == "__main__":
    main()
