# Google Form khảo sát SV ĐH Cần Thơ — THS2026-66

> Soạn: 2026-08-09 · Bản 2 (thêm định danh SV + mở rộng thói quen sinh hoạt)
> Phục vụ task Sprint 0.1–0.3 trong `Sprint_Plan.md`
> Mục tiêu: **N = 150–200** phản hồi · thời lượng **6–8 phút** · **≥60 SV** khai đủ hồ sơ ở ghép

## Nguyên tắc soạn

Mỗi câu phải "nuôi" ít nhất một thứ cụ thể, câu nào không nuôi gì thì **cắt**:

| Mục đích | Ký hiệu |
|---|---|
| Số liệu cho phần "Đặt vấn đề" của báo cáo NCKH | `[BC]` |
| Trọng số / đặc trưng cho module AI | `[AI]` |
| Ghi thẳng vào cột DB | `[DB: bảng.cột]` |
| Tuyển người dùng thật (gỡ nghẽn "chưa có tài khoản SV") | `[USER]` |

**Chống chán — 6 kỹ thuật áp dụng trong form này:**

1. **Cả form chỉ có 2 ô gõ chữ** (họ tên, MSSV) — mọi câu còn lại đều là bấm chọn.
2. **Gộp câu cùng dạng vào Lưới trắc nghiệm** — 8 thói quen nằm gọn 1 màn hình thay vì 8 màn hình.
3. **Câu tình huống có tính giải trí** thay vì hỏi khô ("Bạn cùng phòng ăn hết đồ trong tủ lạnh của bạn…").
4. **Câu A/B chọn nhân vật** — kiểu trắc nghiệm tính cách, SV thấy vui nên trả lời tới cuối.
5. **Bật thanh tiến trình** trong Cài đặt Google Form → thấy sắp xong thì không bỏ ngang.
6. **Đặt phần vui (D) trước phần khai danh tính (F)** — không mở đầu bằng thủ tục hành chính.

Các mốc giá, tiện ích, campus dưới đây **lấy từ dữ liệu thật trong DB**, không tự nghĩ ra.

---

## Phần mở đầu (mô tả form)

> ### 🏠 Bạn đang tìm trọ ở Cần Thơ? Cho tụi mình 6 phút nhé!
>
> Tụi mình là nhóm sinh viên Trường Công nghệ Thông tin & Truyền thông, đang làm đề tài nghiên cứu
> khoa học **THS2026-66** — xây một website gom tin nhà trọ quanh CTU từ nhiều nguồn, có bản đồ chỉ
> đường tới trường, cảnh báo tin lừa đảo, và **gợi ý bạn cùng phòng hợp tính**.
>
> Khảo sát này giúp tụi mình biết SV thật sự cần gì. Gần như toàn bộ là **bấm chọn**, không phải gõ chữ.
>
> **Về thông tin của bạn:**
> - Phần thói quen sinh hoạt và ý kiến của bạn được dùng ở dạng **tổng hợp, không nêu tên** trong báo cáo.
> - Cuối form có hỏi **họ tên và MSSV** — dùng để xác thực bạn là SV CTU và tạo tài khoản dùng thử.
>   Phần này **không bắt buộc**, bạn bỏ trống vẫn gửi được form bình thường.
> - Thông tin cá nhân chỉ nhóm nghiên cứu giữ, **không công khai, không chia sẻ cho bên thứ ba,
>   không dùng cho quảng cáo**, và sẽ xóa sau khi đề tài nghiệm thu (tháng 10/2026).
>
> Cảm ơn bạn nhiều! 🙏

**Cài đặt Google Form cần bật:**
- Hiển thị thanh tiến trình: **Bật**
- Thu thập email tự động: **Tắt** (hỏi thủ công ở cuối, tự nguyện)
- Giới hạn 1 phản hồi/người: **Tắt** (SV hay không đăng nhập Google trường)
- Xáo trộn thứ tự lựa chọn: bật cho câu B2, B4, E1

---

# 📋 PHẦN A — Vài thông tin về bạn (6 câu)

**A1. Bạn hiện là sinh viên Trường Đại học Cần Thơ?** `[sàng lọc]` *(bắt buộc)*
- Có → *chuyển tới Phần B*
- Không → *chuyển tới phần kết thúc*

**A2. Bạn là sinh viên năm mấy?** `[BC]`
- Năm 1 · Năm 2 · Năm 3 · Năm 4 · Năm 5 trở lên · Học viên cao học

**A3. Bạn học ở Trường/Khoa nào?** *(danh sách thả xuống)* `[AI: matching — cùng ngành hiểu nhau hơn]`
- Trường Công nghệ Thông tin & Truyền thông
- Trường Bách khoa
- Trường Kinh tế
- Trường Nông nghiệp
- Trường Thủy sản
- Trường Sư phạm
- Trường Y Dược
- Khoa Khoa học Tự nhiên
- Khoa Khoa học Xã hội & Nhân văn
- Khoa Ngoại ngữ
- Khoa Luật
- Khoa Môi trường & Tài nguyên Thiên nhiên
- Khác

> ⚠️ **Cần kiểm tra lại danh sách này** theo cơ cấu CTU hiện hành trước khi phát — trường đã tái cơ cấu
> từ khoa lên trường sau 2022, tên có thể đã đổi. Sai tên đơn vị là mất điểm chuyên nghiệp ngay câu đầu.
>
> Ngành học là một đặc trưng matching (tài liệu thiết kế gán ~10% trọng số): cùng ngành thì trùng lịch
> học, trùng giờ sinh hoạt, dễ ở chung hơn.

**A4. Bạn học chủ yếu ở khu nào?** `[AI: gốc tính route_time_campus]`
- Khu I (đường 30 Tháng 4)
- Khu II (đường 3 Tháng 2 — khu chính)
- Khu III (đường Lý Tự Trọng)
- Khu Hòa An (Hậu Giang)
- Nhiều khu / tùy học kỳ

**A5. Hiện tại bạn đang ở đâu?** `[BC]`
- Ký túc xá · Nhà trọ (thuê) · Nhà người thân / ở nhờ · Nhà riêng của gia đình · Khác

**A6. Giới tính của bạn** `[DB: roommate_profiles.gender_pref]`
- Nam · Nữ · Không muốn nêu

---

# 🔍 PHẦN B — Chuyện tìm trọ của bạn (6 câu)

*Nguồn số liệu chính cho mục "Đặt vấn đề" của báo cáo.*

**B1. Bạn đã từng tự đi tìm phòng trọ chưa?** `[BC]`
- Rồi, nhiều lần · Rồi, một lần · Chưa từng

**B2. Bạn tìm phòng trọ bằng những cách nào?** *(chọn nhiều)* `[BC]`
- Group Facebook (Nhà trọ Cần Thơ, Chợ SV CTU…)
- Hỏi bạn bè / anh chị khóa trên
- Chạy xe quanh khu vực xem bảng "Cho thuê phòng"
- Website tin đăng (Phongtro123, Chợ Tốt, Mogi…)
- Môi giới / cò nhà trọ
- Hội SV, kênh của trường
- Khác

**B3. Bạn mất bao lâu để tìm được phòng ưng ý?** `[BC]`
- Dưới 3 ngày · 3–7 ngày · 1–2 tuần · Trên 2 tuần · Đến giờ vẫn chưa ưng

**B4. Khó khăn lớn nhất khi tìm trọ là gì?** *(chọn tối đa 3)* `[BC] [AI]`
- Thông tin rải rác nhiều nơi, phải tìm thủ công
- Tin đăng đã cho thuê rồi nhưng chưa gỡ
- Giá đăng khác giá thực tế khi tới xem
- Không biết phòng cách trường bao xa / đi mất bao lâu
- Không có ảnh thật, ảnh không đúng phòng
- Sợ bị lừa đặt cọc
- Không tìm được người ở ghép để chia tiền
- Không biết khu nào an ninh tốt
- Khác

> **Câu quan trọng nhất của cả form.** Mỗi lựa chọn ứng đúng một module đang xây
> (crawler đa nguồn / freshness / risk / route time / matching) → kết quả câu này là biện minh
> định lượng cho toàn bộ kiến trúc đề tài.

**B5. Bạn từng gặp tình huống nào dưới đây chưa?** *(chọn nhiều)* `[BC] [AI: Risk]`
- Liên hệ thì phòng đã cho thuê từ lâu
- Giá thực tế cao hơn giá đăng
- Bị đòi đặt cọc trước khi được xem phòng
- Bị mất tiền cọc
- Phòng thực tế khác hẳn ảnh
- Chưa gặp trường hợp nào

**B6. Bạn tin tưởng thông tin phòng trọ trên mạng ở mức nào?** `[BC]`
Thang 1–5 · 1 = Hoàn toàn không tin · 5 = Rất tin tưởng

---

# 💰 PHẦN C — Bạn cần phòng như thế nào? (5 câu)

*Sinh trọng số cho module Gợi ý.*

**C1. Ngân sách thuê phòng mỗi tháng (chưa tính điện nước):** `[AI] [DB: preference_vector]`
- Dưới 1,5 triệu · 1,5–2 triệu · 2–2,5 triệu · 2,5–3,5 triệu · Trên 3,5 triệu

> Mốc chia theo phân vị giá thật trong DB (p25 = 1,68tr · trung vị = 2tr · p75 = 3tr).

**C2. Bạn dự định ở như thế nào?** `[AI: matching]`
- Ở một mình
- Ở ghép 2 người
- Ở ghép 3 người trở lên
- Ở với người yêu / người thân
- Chưa quyết định

**C3. Mức độ quan trọng của từng yếu tố khi chọn phòng** `[AI: trọng số content-based]`
*(**Lưới trắc nghiệm** — hàng = yếu tố, cột = 1→5)*

| Yếu tố | 1 Không quan trọng → 5 Rất quan trọng |
|---|---|
| Giá thuê rẻ | ○ ○ ○ ○ ○ |
| Gần trường / đi lại nhanh | ○ ○ ○ ○ ○ |
| An ninh khu vực | ○ ○ ○ ○ ○ |
| Tiện nghi (máy lạnh, wifi, WC riêng…) | ○ ○ ○ ○ ○ |
| Giờ giấc tự do, chủ không ở chung | ○ ○ ○ ○ ○ |
| Có chỗ để xe | ○ ○ ○ ○ ○ |
| Gần chợ / quán ăn | ○ ○ ○ ○ ○ |

> Trung bình từng hàng = trọng số khởi tạo cho thuật toán gợi ý. Hội đồng hỏi "trọng số ở đâu ra?"
> thì trả lời bằng số liệu khảo sát, không phải cảm tính của nhóm.

**C4. Bạn chấp nhận đi từ phòng tới trường tối đa bao lâu (xe máy)?** `[AI: route_time_campus]`
- Dưới 5 phút · 5–10 phút · 10–15 phút · 15–20 phút · Trên 20 phút cũng được nếu rẻ

**C5. Tiện ích nào là BẮT BUỘC phải có?** *(chọn nhiều)* `[AI: parsed_amenities]`
- Wifi / internet
- Máy lạnh
- WC riêng trong phòng
- Chỗ để xe
- Được nấu ăn / có bếp
- Tủ lạnh
- Máy giặt
- Giờ giấc tự do
- Gác lửng / có gác

> 8 lựa chọn đầu **trùng khít** từ vựng `AMENITY_KEYWORDS` mà crawler đang parse (`normalize.py:8`).

---

# 🛏️ PHẦN D — Bạn là kiểu bạn cùng phòng nào? (12 câu, bấm chọn hết)

**Mô tả phần:**
> Phần vui nhất đây! Hệ thống của tụi mình có tính năng **gợi ý bạn cùng phòng hợp tính** —
> để làm được thì cần hiểu thói quen sinh hoạt của bạn.
>
> Không có câu trả lời đúng/sai, và **cũng đừng chọn theo kiểu "cho đẹp"** nhé — ghép trúng người
> lệch giờ giấc với mình mới là cực. Cứ chọn đúng thực tế!

> ⚠️ **Vì sao hỏi dạng tình huống chứ không hỏi thẳng "bạn có sạch sẽ không?"** — Đây là bài toán T7
> trong `Technical_Roadmap.md`: hỏi trực tiếp thì ai cũng tự nhận sạch sẽ, hiền lành, ngủ sớm →
> hồ sơ đẹp giả → matching sai. Hỏi qua tình huống cụ thể thì khó khai đẹp hơn nhiều.

## D1–D4 · Nhịp sinh hoạt

**D1. Ngày thường, bạn đi ngủ lúc mấy giờ?** `[DB: sleep_time]`
- Trước 22h → `0`
- 22h – 24h → `1`
- Sau 0h → `2`

**D2. Còn thức dậy?** `[AI: bổ trợ sleep_time]`
- Trước 6h · 6h–7h30 · 7h30–9h · Sau 9h · Tùy hôm, không cố định

**D3. Bạn cùng phòng bật nhạc / xem phim lúc 23h. Bạn sẽ:** `[DB: noise_tolerance]`
- Không sao cả, mình vẫn ngủ được → `5`
- Hơi khó chịu nhưng không nói gì → `3`
- Nhắc nhẹ bạn vặn nhỏ lại → `2`
- Rất khó chịu, phải nói thẳng ngay → `1`

**D4. Cuối tuần bạn thường:**
- Ở phòng là chính · Ra ngoài là chính · Về nhà / quê

## D5–D7 · Chuyện dọn dẹp

**D5. Chén bát sau khi ăn xong, bạn thường:** `[DB: cleanliness]`
- Rửa ngay lập tức → `5`
- Rửa trong ngày hôm đó → `4`
- Để 1–2 ngày rồi rửa một lượt → `3`
- Để đến khi hết chén sạch → `2`
- Thường để người khác rửa → `1`

**D6. Nhà vệ sinh / khu vực chung trong phòng trọ:** `[AI: bổ trợ cleanliness]`
- Mình chủ động dọn thường xuyên
- Chia lịch rõ ràng thì mình theo
- Ai rảnh người đó dọn
- Thú thật là mình ít khi dọn

**D7. Đồ đạc cá nhân của bạn (quần áo, sách vở, đồ dùng):** `[AI: bổ trợ cleanliness]`
- Luôn gọn gàng, đâu ra đó
- Gọn được vài hôm rồi lại bừa
- Bừa nhưng mình biết đồ ở đâu
- Khá bừa, mình cũng hay tìm không ra đồ

## D8–D10 · Mấy chuyện dễ gây mâu thuẫn

**D8. Về thuốc lá:** `[DB: smoke]`
- Mình có hút và cần hút trong phòng
- Mình có hút nhưng ra ngoài hút
- Mình không hút, và **không** chịu được người ở chung hút
- Mình không hút, nhưng người khác hút thì cũng được

**D9. Tiền điện máy lạnh — bạn thuộc kiểu nào?** `[AI: nguồn mâu thuẫn phổ biến nhất]`
- Bật máy lạnh gần như cả đêm, tiền điện bao nhiêu cũng được
- Bật lúc nóng thôi, có ý thức tiết kiệm
- Ít khi bật, quạt là đủ
- Mình rất để ý tiền điện, hay nhắc nhau tắt

**D10. Chuyện tiền nong khi ở chung:** `[AI]`
- Chia sòng phẳng từng khoản, tính rõ ràng ngay
- Chia đều cho nhanh, không tính chi li
- Ai ứng trước cũng được, cuối tháng gom lại
- Mình ngại nói chuyện tiền bạc

## D11 · Lưới thói quen (1 màn hình — nhanh gọn)

**D11. Mức độ đúng với bạn:** *(**Lưới trắc nghiệm** · 1 = Không đúng chút nào → 5 = Rất đúng)* `[AI: matching_vector]`

| Điều này đúng với bạn ở mức nào? | 1 → 5 |
|---|---|
| Mình hay nấu ăn trong phòng | ○ ○ ○ ○ ○ |
| Mình hay rủ bạn bè về phòng chơi | ○ ○ ○ ○ ○ |
| Mình cần không gian yên tĩnh để học bài | ○ ○ ○ ○ ○ |
| Mình thích trò chuyện với bạn cùng phòng | ○ ○ ○ ○ ○ |
| Mình sẵn sàng dùng chung đồ (đồ ăn, đồ dùng) | ○ ○ ○ ○ ○ |
| Mình hay nhậu / tụ tập bạn bè | ○ ○ ○ ○ ○ |
| Mình muốn nuôi thú cưng trong phòng | ○ ○ ○ ○ ○ |
| Mình hay đi chơi về khuya | ○ ○ ○ ○ ○ |

> 8 câu này nếu tách rời là 8 màn hình, SV bỏ ngang giữa chừng. Gộp lưới thì **20 giây xong**,
> mà vẫn thu đủ 8 chiều đặc trưng cho vector matching.

## D12–D14 · Chốt hồ sơ

**D12. Bạn giống người nào hơn?** *(chọn 1)* `[AI: forced choice — kiểu trắc nghiệm cho vui]`
- 🌙 **An** — ngủ trễ dậy trễ, phòng hơi bừa nhưng dễ tính, ai làm gì cũng kệ
- ☀️ **Bình** — ngủ sớm dậy sớm, thích phòng gọn gàng, cần yên tĩnh để học

> Câu này ép chọn giữa 2 cực, không cho chọn "ở giữa" → lộ xu hướng thật.
> SV thấy vui vì giống trắc nghiệm tính cách, mà thực chất là một chiều đặc trưng mạnh.

**D13. Bạn muốn ở ghép với:** `[DB: gender_pref]`
- Cùng giới tính với mình → `1`/`2`
- Giới tính nào cũng được → `0`
- Mình không có nhu cầu ở ghép

**D14. Điều bạn KHÔNG chấp nhận được ở người ở ghép:** *(chọn nhiều)* `[AI: bộ lọc cứng]`
- Hút thuốc trong phòng
- Ở bẩn, không dọn dẹp
- Ồn ào khuya
- Hay dẫn bạn về phòng
- Người yêu ở lại qua đêm
- Nuôi thú cưng
- Nhậu nhẹt trong phòng
- Trả tiền trọ trễ
- Không có điều nào đặc biệt, mình dễ tính

> Nhóm này **không** đưa vào cosine similarity — nó là **bộ lọc cứng chạy trước khi tính điểm**.
> Người "hút thuốc trong phòng" ghép với người chọn deal-breaker này thì similarity 0.95 vẫn phải loại.

---

# 💡 PHẦN E — Ý kiến về hệ thống (2 câu)

**Mô tả phần:**
> Sắp xong rồi! Tụi mình đang xây website gom tin trọ quanh CTU từ nhiều nguồn, có bản đồ và vài tính năng AI.

**E1. Tính năng nào bạn thấy hữu ích nhất?** *(chọn tối đa 3)* `[BC: ưu tiên phát triển]`
- Gom tin trọ từ nhiều trang về một chỗ
- Bản đồ hiển thị phòng + số phút đi tới trường
- Cảnh báo tin có dấu hiệu rủi ro / lừa đảo
- Gợi ý phòng hợp gu dựa trên sở thích của bạn
- Tìm bạn cùng phòng phù hợp tính cách
- Chatbot hỏi đáp bằng tiếng Việt ("phòng 2 triệu gần khu II có máy lạnh?")
- Thông báo khi có phòng mới khớp tiêu chí

**E2. Nếu có chatbot, bạn thấy cách nào tiện hơn?** `[BC: validate RAG]`
- Hỏi chatbot bằng câu tự nhiên tiện hơn
- Tự bấm bộ lọc tiện hơn
- Tùy lúc, có cả hai thì tốt

---

# 🎓 PHẦN F — Đăng ký dùng thử (4 câu, không bắt buộc)

**Mô tả phần:**
> **Muốn dùng thử hệ thống + được ghép bạn cùng phòng?** Để lại thông tin bên dưới nhé.
>
> Tính năng ghép bạn ở của tụi mình **chỉ ghép giữa các SV CTU đã xác thực bằng MSSV** — để bạn
> yên tâm là người được ghép cũng là sinh viên trường mình, không phải người lạ trên mạng.
>
> Thông tin này **nhóm nghiên cứu giữ riêng**, không công khai. Người được ghép chỉ thấy tên và
> thói quen sinh hoạt của bạn **sau khi cả hai bên cùng đồng ý kết nối** — không ai xem được
> MSSV hay số điện thoại của bạn nếu bạn chưa chấp nhận.
>
> Bạn để trống phần này vẫn gửi form được bình thường.

**F1. Bạn có muốn dùng thử website và được ghép bạn cùng phòng không?** *(bắt buộc)* `[USER]`
- Có, mình muốn dùng thử → *chuyển tới phần F-phụ (F2–F4)*
- Không, mình chỉ tham gia khảo sát thôi → *chuyển tới phần cảm ơn*

> ⚙️ **Cách siết để không có hồ sơ khai nửa vời:** tách F2–F4 ra thành **một phần riêng** trong
> Google Form, dùng "Chuyển phần dựa trên câu trả lời" ở F1. Trong phần đó, đặt F2, F3
> **bắt buộc**. Người chọn "Không" không bao giờ nhìn thấy phần này nên không bị chặn;
> người chọn "Có" thì buộc khai đủ tên + MSSV mới gửi được form.
>
> Đây là điểm cân bằng đúng: **không mất phiếu khảo sát** của người không có nhu cầu ở ghép,
> mà **không có hồ sơ ghép nào bị thiếu định danh**.

**F2. Họ và tên của bạn** *(câu trả lời ngắn — 1 trong 2 ô gõ chữ của cả form)* `[USER] [DB: users.name]`

**F3. Mã số sinh viên** *(câu trả lời ngắn)* `[USER] [xác thực SV CTU]`
*Ví dụ: B2105678. Dùng để xác nhận bạn là SV CTU, không hiển thị cho ai khác.*

> 🔑 MSSV làm **3 việc** cùng lúc: (1) xác thực SV thật → tính năng ghép bạn có giá trị tin cậy,
> đây là điểm hệ thống hơn hẳn group Facebook; (2) chống trùng phiếu / phiếu rác trong mẫu khảo sát;
> (3) MSSV CTU mã hóa sẵn khóa tuyển sinh → chéo kiểm với câu A2 (năm mấy) để phát hiện phiếu điền ẩu.

**F4. Email hoặc số Zalo để tụi mình liên hệ** *(câu trả lời ngắn)* `[USER]`
*Chỉ dùng gửi link dùng thử, không spam.*

**Phần kết thúc:**
> Xong rồi, cảm ơn bạn siêu nhiều! 🎉
> Khi website chạy được, tụi mình sẽ gửi link cho bạn dùng thử đầu tiên.
> Có góp ý gì thêm, nhắn tụi mình qua [link fanpage / Zalo nhóm].

---

# ⚙️ Ảnh hưởng tới schema — cần làm trước khi nhập liệu

Bảng `roommate_profiles` hiện chỉ có 5 trường (`30_users.sql:20`), **không chứa nổi** các thói quen
mở rộng ở D2, D6, D7, D9, D10, D11, D12. Cần một migration trước khi đổ dữ liệu khảo sát vào:

```sql
-- infra/db/migrations/80_roommate_habits.sql  (chưa tạo)
ALTER TABLE roommate_profiles
    ADD COLUMN wake_time        INTEGER,   -- D2
    ADD COLUMN shared_clean     INTEGER,   -- D6
    ADD COLUMN tidiness         INTEGER,   -- D7
    ADD COLUMN aircon_usage     INTEGER,   -- D9  (nguồn mâu thuẫn hay gặp nhất)
    ADD COLUMN money_style      INTEGER,   -- D10
    ADD COLUMN habits           JSONB,     -- D11 lưới 8 chiều
    ADD COLUMN persona          SMALLINT,  -- D12 forced choice A/B
    ADD COLUMN deal_breakers    JSONB,     -- D14 bộ lọc cứng
    ADD COLUMN faculty          VARCHAR(100),  -- A3
    ADD COLUMN student_code     VARCHAR(20);   -- F3
CREATE UNIQUE INDEX idx_roommate_student_code
    ON roommate_profiles (student_code) WHERE student_code IS NOT NULL;
```

Tổng số chiều đặc trưng sau khi mở rộng: **~20 chiều** (5 cũ + 15 mới), thừa sức dựng
`matching_vector` có ý nghĩa thay vì 5 chiều nghèo nàn như thiết kế ban đầu.

**Lưu ý bảo mật khi triển khai:** `student_code` và số điện thoại **không được** nằm trong response
của API ghép bạn cho tới khi `match_requests.status = 'accepted'` — đúng nguyên tắc FR-5.3
("B chấp nhận → lộ liên hệ 2 chiều"). Đây là chỗ rất dễ lộ dữ liệu do vô ý trả cả object user.

---

# 🔗 Form khảo sát ≠ hệ thống ghép bạn — hai nguồn hồ sơ khác nhau

Cần phân biệt rõ, vì nhầm chỗ này dẫn tới thiết kế sai:

| | Google Form | Trong app |
|---|---|---|
| Vai trò | **Phễu tuyển** người dùng đầu tiên | **Nguồn hồ sơ chính thức** |
| Ghi vào đâu | CSV → nhập tay vào `users` + `roommate_profiles` | `roommate_profiles` qua form trong app (FR-5.1) |
| Khi nào | Tháng 8/2026, một lần | Liên tục, mỗi user mới đăng ký |
| Sửa được không | Không (SV đã gửi form là xong) | Có, user tự cập nhật hồ sơ |

Form chỉ giải bài toán **khởi động nguội**: hệ thống mới ra không có ai để ghép, nên cần một mồi
40–60 hồ sơ thật. Sau đó nguồn hồ sơ là chính người dùng đăng ký tài khoản và tự điền trong app —
lúc đó tên và MSSV là **trường bắt buộc khi bật tính năng ghép bạn**, không còn tự nguyện nữa.

Nói cách khác: **tự nguyện ở form, bắt buộc trong app.** Ai muốn dùng tính năng ghép bạn thì phải
xác thực MSSV — đó là điều kiện dùng tính năng, hợp lý và SV chấp nhận được. Còn ép khai MSSV để
đổi lấy việc trả lời một bản khảo sát nghiên cứu thì SV sẽ thoát form.

---

# 📢 Kế hoạch phát form

| Việc | Chi tiết |
|---|---|
| Kênh phát | Group Zalo lớp (nhờ lớp trưởng đăng), group FB "Sinh viên CTU" / "Nhà trọ Cần Thơ", story cá nhân cả 5 thành viên |
| Ưu tiên | SV **năm 1 và năm 2** — đang thuê hoặc sắp thuê, trả lời sát thực tế nhất |
| Thời gian | Phát tuần 09–15/08, chốt số liệu **31/08** |
| Mục tiêu | ≥150 phản hồi · ≥60 hồ sơ ở ghép đầy đủ · ≥40 người để lại liên hệ |
| Thúc đẩy | Đăng lại lần 2 sau 5 ngày; câu mở đầu nêu rõ "6 phút, bấm chọn là chính" |
| Xử lý | Tải CSV → `docs/planning/khao_sat_ket_qua.csv` → phân tích pandas → biểu đồ cho báo cáo (task 0.3) |

## Bẫy cần tránh

- **Đừng đưa tên/MSSV lên đầu form.** Đặt ở cuối như bố cục trên. Lên đầu thì SV trả lời phần thói
  quen theo kiểu "khai cho đẹp" vì thấy tên mình gắn vào — hỏng đúng phần cần nhất.
- **Đừng để F2–F4 ở chế độ bắt buộc.** Bắt buộc khai MSSV sẽ mất khoảng một nửa số phản hồi,
  trong khi phần A–E vẫn có giá trị đầy đủ cho báo cáo dù không biết người trả lời là ai.
- **Đừng hỏi số điện thoại riêng** — gộp chung ô "email hoặc Zalo" ở F4, ai thoải mái thì cho.
- **Đừng đổi câu chữ sau khi đã phát.** Mỗi lần sửa là dữ liệu trước/sau không gộp được.
- **Kiểm tra lại tên Trường/Khoa ở A3** theo cơ cấu CTU hiện tại trước khi phát.

---

# 📊 Form thứ 2 — ground-truth cho đánh giá Gợi ý (làm ~tháng 9)

Form trên **không** đo được Precision@10 — chỉ tiêu nghiệm thu ≥0,6 của module Gợi ý.
Cần form ngắn thứ hai, gửi riêng cho những người đã để lại liên hệ ở F4:

1. Hỏi lại nhanh 4 tiêu chí (ngân sách, khu học, khoảng cách tối đa, 2 tiện ích bắt buộc).
2. Hiển thị **15–20 tin trọ thật lấy từ DB** (ảnh + giá + địa chỉ + phút tới trường), xáo trộn thứ tự.
3. Hỏi: *"Tin nào bạn sẽ thật sự bấm gọi cho chủ trọ?"* (chọn nhiều).

Tin được chọn = nhãn `relevant`. Đưa 4 tiêu chí ở bước 1 vào thuật toán, so top-10 nó trả ra với
danh sách người thật chọn → ra **Precision@10 và NDCG@10 thật**, không phải số tự nghĩ.
Đây là bộ số hội đồng sẽ hỏi tới.
