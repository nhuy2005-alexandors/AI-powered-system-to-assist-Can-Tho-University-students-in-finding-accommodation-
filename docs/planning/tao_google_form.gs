/**
 * Tạo Google Form khảo sát SV ĐH Cần Thơ — đề tài THS2026-66
 * Nội dung khớp docs/planning/Khao_Sat_SV_Form.md
 *
 * CÁCH CHẠY:
 *   1. Vào https://script.google.com  → "Dự án mới" (New project)
 *   2. Xóa hết code mẫu, dán TOÀN BỘ file này vào
 *   3. Bấm Lưu (💾) → đặt tên dự án tùy ý
 *   4. Chọn hàm `taoFormKhaoSat` ở thanh trên → bấm ▶ Chạy
 *   5. Lần đầu Google hỏi quyền → Xem lại quyền → chọn tài khoản →
 *      "Nâng cao" → "Chuyển đến ... (không an toàn)" → Cho phép
 *      (cảnh báo này là bình thường với script tự viết, chưa được Google duyệt)
 *   6. Xem tab "Nhật ký thực thi" (Execution log) → có 2 link:
 *      LINK GỬI SV  → link phát cho sinh viên
 *      LINK CHỈNH SỬA → link mở form để sửa
 *
 * SAU KHI CHẠY — 2 việc phải làm tay (Apps Script không đặt được):
 *   a) Bật "Xáo trộn thứ tự lựa chọn" cho câu B2, B4, E1
 *      (mở form → bấm ⋮ ở góc câu → "Xáo trộn thứ tự lựa chọn")
 *   b) Kiểm tra lại danh sách Trường/Khoa ở câu A3 theo cơ cấu CTU hiện hành
 */

function taoFormKhaoSat() {
  const form = FormApp.create('Khảo sát nhu cầu tìm nhà trọ của sinh viên ĐH Cần Thơ');

  form.setDescription(
    '🏠 Bạn đang tìm trọ ở Cần Thơ? Cho tụi mình 6 phút nhé!\n\n' +
    'Tụi mình là nhóm sinh viên Trường Công nghệ Thông tin & Truyền thông, đang làm đề tài ' +
    'nghiên cứu khoa học THS2026-66 — xây một website gom tin nhà trọ quanh CTU từ nhiều nguồn, ' +
    'có bản đồ chỉ đường tới trường, cảnh báo tin lừa đảo, và gợi ý bạn cùng phòng hợp tính.\n\n' +
    'Khảo sát này giúp tụi mình biết SV thật sự cần gì. Gần như toàn bộ là BẤM CHỌN, không phải gõ chữ.\n\n' +
    '── Về thông tin của bạn ──\n' +
    '• Phần thói quen sinh hoạt và ý kiến của bạn được dùng ở dạng tổng hợp, không nêu tên trong báo cáo.\n' +
    '• Cuối form có hỏi họ tên và MSSV — dùng để xác thực bạn là SV CTU và tạo tài khoản dùng thử. ' +
    'Phần này KHÔNG BẮT BUỘC, bạn bỏ qua vẫn gửi được form bình thường.\n' +
    '• Thông tin cá nhân chỉ nhóm nghiên cứu giữ, không công khai, không chia sẻ cho bên thứ ba, ' +
    'không dùng cho quảng cáo, và sẽ xóa sau khi đề tài nghiệm thu (tháng 10/2026).\n\n' +
    'Cảm ơn bạn nhiều! 🙏'
  );

  form.setProgressBar(true);
  form.setCollectEmail(false);
  form.setLimitOneResponsePerUser(false);
  form.setAllowResponseEdits(false);
  form.setConfirmationMessage(
    'Xong rồi, cảm ơn bạn siêu nhiều! 🎉\n\n' +
    'Khi website chạy được, tụi mình sẽ gửi link cho bạn dùng thử đầu tiên.'
  );

  // ══════════════════════════════════════════════════════════════
  // TRANG 0 — câu sàng lọc (phải đứng một mình để phân nhánh được)
  // ══════════════════════════════════════════════════════════════
  const a1 = form.addMultipleChoiceItem()
    .setTitle('Bạn hiện là sinh viên Trường Đại học Cần Thơ?')
    .setRequired(true);

  // ══════════════════════════════════════════════════════════════
  // PHẦN A — Thông tin chung
  // ══════════════════════════════════════════════════════════════
  const trangA = form.addPageBreakItem()
    .setTitle('📋 Phần A — Vài thông tin về bạn');

  form.addMultipleChoiceItem()
    .setTitle('Bạn là sinh viên năm mấy?')
    .setChoiceValues(['Năm 1', 'Năm 2', 'Năm 3', 'Năm 4', 'Năm 5 trở lên', 'Học viên cao học'])
    .setRequired(true);

  form.addListItem()
    .setTitle('Bạn học ở Trường/Khoa nào?')
    .setChoiceValues([
      'Trường Công nghệ Thông tin & Truyền thông',
      'Trường Bách khoa',
      'Trường Kinh tế',
      'Trường Nông nghiệp',
      'Trường Thủy sản',
      'Trường Sư phạm',
      'Trường Y Dược',
      'Khoa Khoa học Tự nhiên',
      'Khoa Khoa học Xã hội & Nhân văn',
      'Khoa Ngoại ngữ',
      'Khoa Luật',
      'Khoa Môi trường & Tài nguyên Thiên nhiên',
      'Khác'
    ])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('Bạn học chủ yếu ở khu nào?')
    .setChoiceValues([
      'Khu I (đường 30 Tháng 4)',
      'Khu II (đường 3 Tháng 2 — khu chính)',
      'Khu III (đường Lý Tự Trọng)',
      'Khu Hòa An (Hậu Giang)',
      'Nhiều khu / tùy học kỳ'
    ])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('Hiện tại bạn đang ở đâu?')
    .setChoiceValues([
      'Ký túc xá',
      'Nhà trọ (thuê)',
      'Nhà người thân / ở nhờ',
      'Nhà riêng của gia đình',
      'Khác'
    ])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('Giới tính của bạn')
    .setChoiceValues(['Nam', 'Nữ', 'Không muốn nêu'])
    .setRequired(true);

  // ══════════════════════════════════════════════════════════════
  // PHẦN B — Trải nghiệm tìm trọ
  // ══════════════════════════════════════════════════════════════
  form.addPageBreakItem()
    .setTitle('🔍 Phần B — Chuyện tìm trọ của bạn');

  form.addMultipleChoiceItem()
    .setTitle('Bạn đã từng tự đi tìm phòng trọ chưa?')
    .setChoiceValues(['Rồi, nhiều lần', 'Rồi, một lần', 'Chưa từng'])
    .setRequired(true);

  form.addCheckboxItem()
    .setTitle('Bạn tìm phòng trọ bằng những cách nào?')
    .setHelpText('Chọn nhiều đáp án')
    .setChoiceValues([
      'Group Facebook (Nhà trọ Cần Thơ, Chợ SV CTU…)',
      'Hỏi bạn bè / anh chị khóa trên',
      'Chạy xe quanh khu vực xem bảng "Cho thuê phòng"',
      'Website tin đăng (Phongtro123, Chợ Tốt, Mogi…)',
      'Môi giới / cò nhà trọ',
      'Hội SV, kênh của trường',
      'Khác'
    ]);

  form.addMultipleChoiceItem()
    .setTitle('Bạn mất bao lâu để tìm được phòng ưng ý?')
    .setChoiceValues([
      'Dưới 3 ngày',
      '3–7 ngày',
      '1–2 tuần',
      'Trên 2 tuần',
      'Đến giờ vẫn chưa ưng'
    ]);

  const b4 = form.addCheckboxItem()
    .setTitle('Khó khăn lớn nhất khi tìm trọ là gì?')
    .setHelpText('Chọn tối đa 3 đáp án')
    .setChoiceValues([
      'Thông tin rải rác nhiều nơi, phải tìm thủ công',
      'Tin đăng đã cho thuê rồi nhưng chưa gỡ',
      'Giá đăng khác giá thực tế khi tới xem',
      'Không biết phòng cách trường bao xa / đi mất bao lâu',
      'Không có ảnh thật, ảnh không đúng phòng',
      'Sợ bị lừa đặt cọc',
      'Không tìm được người ở ghép để chia tiền',
      'Không biết khu nào an ninh tốt',
      'Khác'
    ])
    .setRequired(true);
  b4.setValidation(FormApp.createCheckboxValidation().requireSelectAtMost(3).build());

  form.addCheckboxItem()
    .setTitle('Bạn từng gặp tình huống nào dưới đây chưa?')
    .setHelpText('Chọn nhiều đáp án')
    .setChoiceValues([
      'Liên hệ thì phòng đã cho thuê từ lâu',
      'Giá thực tế cao hơn giá đăng',
      'Bị đòi đặt cọc trước khi được xem phòng',
      'Bị mất tiền cọc',
      'Phòng thực tế khác hẳn ảnh',
      'Chưa gặp trường hợp nào'
    ]);

  form.addScaleItem()
    .setTitle('Bạn tin tưởng thông tin phòng trọ trên mạng ở mức nào?')
    .setBounds(1, 5)
    .setLabels('Hoàn toàn không tin', 'Rất tin tưởng')
    .setRequired(true);

  // ══════════════════════════════════════════════════════════════
  // PHẦN C — Tiêu chí chọn phòng
  // ══════════════════════════════════════════════════════════════
  form.addPageBreakItem()
    .setTitle('💰 Phần C — Bạn cần phòng như thế nào?');

  form.addMultipleChoiceItem()
    .setTitle('Ngân sách thuê phòng mỗi tháng của bạn (chưa tính điện nước)')
    .setChoiceValues([
      'Dưới 1,5 triệu',
      '1,5 – 2 triệu',
      '2 – 2,5 triệu',
      '2,5 – 3,5 triệu',
      'Trên 3,5 triệu'
    ])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('Bạn dự định ở như thế nào?')
    .setChoiceValues([
      'Ở một mình',
      'Ở ghép 2 người',
      'Ở ghép 3 người trở lên',
      'Ở với người yêu / người thân',
      'Chưa quyết định'
    ])
    .setRequired(true);

  form.addGridItem()
    .setTitle('Mức độ quan trọng của từng yếu tố khi bạn chọn phòng')
    .setHelpText('1 = Không quan trọng · 5 = Rất quan trọng')
    .setRows([
      'Giá thuê rẻ',
      'Gần trường / đi lại nhanh',
      'An ninh khu vực',
      'Tiện nghi (máy lạnh, wifi, WC riêng…)',
      'Giờ giấc tự do, chủ không ở chung',
      'Có chỗ để xe',
      'Gần chợ / quán ăn'
    ])
    .setColumns(['1', '2', '3', '4', '5'])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('Bạn chấp nhận đi từ phòng tới trường tối đa bao lâu? (xe máy)')
    .setChoiceValues([
      'Dưới 5 phút',
      '5–10 phút',
      '10–15 phút',
      '15–20 phút',
      'Trên 20 phút cũng được nếu rẻ'
    ])
    .setRequired(true);

  form.addCheckboxItem()
    .setTitle('Tiện ích nào là BẮT BUỘC phải có?')
    .setHelpText('Chọn nhiều đáp án')
    .setChoiceValues([
      'Wifi / internet',
      'Máy lạnh',
      'WC riêng trong phòng',
      'Chỗ để xe',
      'Được nấu ăn / có bếp',
      'Tủ lạnh',
      'Máy giặt',
      'Giờ giấc tự do',
      'Gác lửng / có gác'
    ]);

  // ══════════════════════════════════════════════════════════════
  // PHẦN D — Hồ sơ ở ghép
  // ══════════════════════════════════════════════════════════════
  form.addPageBreakItem()
    .setTitle('🛏️ Phần D — Bạn là kiểu bạn cùng phòng nào?')
    .setHelpText(
      'Phần vui nhất đây! Hệ thống của tụi mình có tính năng gợi ý bạn cùng phòng hợp tính — ' +
      'để làm được thì cần hiểu thói quen sinh hoạt của bạn.\n\n' +
      'Không có câu trả lời đúng/sai, và cũng đừng chọn theo kiểu "cho đẹp" nhé — ' +
      'ghép trúng người lệch giờ giấc với mình mới là cực. Cứ chọn đúng thực tế!'
    );

  // --- Nhịp sinh hoạt ---
  form.addMultipleChoiceItem()
    .setTitle('Ngày thường, bạn đi ngủ lúc mấy giờ?')
    .setChoiceValues(['Trước 22h', '22h – 24h', 'Sau 0h'])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('Còn thức dậy?')
    .setChoiceValues(['Trước 6h', '6h – 7h30', '7h30 – 9h', 'Sau 9h', 'Tùy hôm, không cố định'])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('Bạn cùng phòng bật nhạc / xem phim lúc 23h. Bạn sẽ:')
    .setChoiceValues([
      'Không sao cả, mình vẫn ngủ được',
      'Hơi khó chịu nhưng không nói gì',
      'Nhắc nhẹ bạn vặn nhỏ lại',
      'Rất khó chịu, phải nói thẳng ngay'
    ])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('Cuối tuần bạn thường:')
    .setChoiceValues(['Ở phòng là chính', 'Ra ngoài là chính', 'Về nhà / quê'])
    .setRequired(true);

  // --- Dọn dẹp ---
  form.addMultipleChoiceItem()
    .setTitle('Chén bát sau khi ăn xong, bạn thường:')
    .setChoiceValues([
      'Rửa ngay lập tức',
      'Rửa trong ngày hôm đó',
      'Để 1–2 ngày rồi rửa một lượt',
      'Để đến khi hết chén sạch',
      'Thường để người khác rửa'
    ])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('Nhà vệ sinh / khu vực chung trong phòng trọ:')
    .setChoiceValues([
      'Mình chủ động dọn thường xuyên',
      'Chia lịch rõ ràng thì mình theo',
      'Ai rảnh người đó dọn',
      'Thú thật là mình ít khi dọn'
    ])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('Đồ đạc cá nhân của bạn (quần áo, sách vở, đồ dùng):')
    .setChoiceValues([
      'Luôn gọn gàng, đâu ra đó',
      'Gọn được vài hôm rồi lại bừa',
      'Bừa nhưng mình biết đồ ở đâu',
      'Khá bừa, mình cũng hay tìm không ra đồ'
    ])
    .setRequired(true);

  // --- Mấy chuyện dễ gây mâu thuẫn ---
  form.addMultipleChoiceItem()
    .setTitle('Về thuốc lá:')
    .setChoiceValues([
      'Mình có hút và cần hút trong phòng',
      'Mình có hút nhưng ra ngoài hút',
      'Mình không hút, và KHÔNG chịu được người ở chung hút',
      'Mình không hút, nhưng người khác hút thì cũng được'
    ])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('Tiền điện máy lạnh — bạn thuộc kiểu nào?')
    .setChoiceValues([
      'Bật máy lạnh gần như cả đêm, tiền điện bao nhiêu cũng được',
      'Bật lúc nóng thôi, có ý thức tiết kiệm',
      'Ít khi bật, quạt là đủ',
      'Mình rất để ý tiền điện, hay nhắc nhau tắt'
    ])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('Chuyện tiền nong khi ở chung:')
    .setChoiceValues([
      'Chia sòng phẳng từng khoản, tính rõ ràng ngay',
      'Chia đều cho nhanh, không tính chi li',
      'Ai ứng trước cũng được, cuối tháng gom lại',
      'Mình ngại nói chuyện tiền bạc'
    ])
    .setRequired(true);

  // --- Lưới thói quen ---
  form.addGridItem()
    .setTitle('Mấy điều dưới đây đúng với bạn ở mức nào?')
    .setHelpText('1 = Không đúng chút nào · 5 = Rất đúng')
    .setRows([
      'Mình hay nấu ăn trong phòng',
      'Mình hay rủ bạn bè về phòng chơi',
      'Mình cần không gian yên tĩnh để học bài',
      'Mình thích trò chuyện với bạn cùng phòng',
      'Mình sẵn sàng dùng chung đồ (đồ ăn, đồ dùng)',
      'Mình hay nhậu / tụ tập bạn bè',
      'Mình muốn nuôi thú cưng trong phòng',
      'Mình hay đi chơi về khuya'
    ])
    .setColumns(['1', '2', '3', '4', '5'])
    .setRequired(true);

  // --- Chốt hồ sơ ---
  form.addMultipleChoiceItem()
    .setTitle('Bạn giống người nào hơn?')
    .setHelpText('Chọn 1 người bạn thấy giống mình hơn — kể cả khi không giống hoàn toàn')
    .setChoiceValues([
      '🌙 An — ngủ trễ dậy trễ, phòng hơi bừa nhưng dễ tính, ai làm gì cũng kệ',
      '☀️ Bình — ngủ sớm dậy sớm, thích phòng gọn gàng, cần yên tĩnh để học'
    ])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('Bạn muốn ở ghép với:')
    .setChoiceValues([
      'Cùng giới tính với mình',
      'Giới tính nào cũng được',
      'Mình không có nhu cầu ở ghép'
    ])
    .setRequired(true);

  form.addCheckboxItem()
    .setTitle('Điều bạn KHÔNG chấp nhận được ở người ở ghép:')
    .setHelpText('Chọn nhiều đáp án')
    .setChoiceValues([
      'Hút thuốc trong phòng',
      'Ở bẩn, không dọn dẹp',
      'Ồn ào khuya',
      'Hay dẫn bạn về phòng',
      'Người yêu ở lại qua đêm',
      'Nuôi thú cưng',
      'Nhậu nhẹt trong phòng',
      'Trả tiền trọ trễ',
      'Không có điều nào đặc biệt, mình dễ tính'
    ])
    .setRequired(true);

  // ══════════════════════════════════════════════════════════════
  // PHẦN E — Ý kiến về hệ thống
  // ══════════════════════════════════════════════════════════════
  form.addPageBreakItem()
    .setTitle('💡 Phần E — Ý kiến về hệ thống')
    .setHelpText(
      'Sắp xong rồi! Tụi mình đang xây website gom tin trọ quanh CTU từ nhiều nguồn, ' +
      'có bản đồ và vài tính năng AI.'
    );

  const e1 = form.addCheckboxItem()
    .setTitle('Tính năng nào bạn thấy hữu ích nhất?')
    .setHelpText('Chọn tối đa 3 đáp án')
    .setChoiceValues([
      'Gom tin trọ từ nhiều trang về một chỗ',
      'Bản đồ hiển thị phòng + số phút đi tới trường',
      'Cảnh báo tin có dấu hiệu rủi ro / lừa đảo',
      'Gợi ý phòng hợp gu dựa trên sở thích của bạn',
      'Tìm bạn cùng phòng phù hợp tính cách',
      'Chatbot hỏi đáp bằng tiếng Việt ("phòng 2 triệu gần khu II có máy lạnh?")',
      'Thông báo khi có phòng mới khớp tiêu chí'
    ])
    .setRequired(true);
  e1.setValidation(FormApp.createCheckboxValidation().requireSelectAtMost(3).build());

  form.addMultipleChoiceItem()
    .setTitle('Nếu có chatbot, bạn thấy cách nào tiện hơn?')
    .setChoiceValues([
      'Hỏi chatbot bằng câu tự nhiên tiện hơn',
      'Tự bấm bộ lọc tiện hơn',
      'Tùy lúc, có cả hai thì tốt'
    ])
    .setRequired(true);

  // ══════════════════════════════════════════════════════════════
  // PHẦN F — câu rẽ nhánh (đứng một mình cuối trang)
  // ══════════════════════════════════════════════════════════════
  form.addPageBreakItem()
    .setTitle('🎓 Phần F — Đăng ký dùng thử')
    .setHelpText(
      'Muốn dùng thử hệ thống + được ghép bạn cùng phòng? Để lại thông tin ở bước sau nhé.\n\n' +
      'Tính năng ghép bạn ở của tụi mình CHỈ ghép giữa các SV CTU đã xác thực bằng MSSV — ' +
      'để bạn yên tâm là người được ghép cũng là sinh viên trường mình, không phải người lạ trên mạng.\n\n' +
      'Thông tin này nhóm nghiên cứu giữ riêng, không công khai. Người được ghép chỉ thấy tên và ' +
      'thói quen sinh hoạt của bạn SAU KHI cả hai bên cùng đồng ý kết nối — không ai xem được ' +
      'MSSV hay số liên hệ của bạn nếu bạn chưa chấp nhận.'
    );

  const f1 = form.addMultipleChoiceItem()
    .setTitle('Bạn có muốn dùng thử website và được ghép bạn cùng phòng không?')
    .setRequired(true);

  // ══════════════════════════════════════════════════════════════
  // PHẦN F-phụ — chỉ hiện khi chọn "Có" ⇒ tên + MSSV BẮT BUỘC
  // ══════════════════════════════════════════════════════════════
  const trangFChiTiet = form.addPageBreakItem()
    .setTitle('🎓 Thông tin để tạo tài khoản dùng thử');

  form.addTextItem()
    .setTitle('Họ và tên của bạn')
    .setRequired(true);

  form.addTextItem()
    .setTitle('Mã số sinh viên')
    .setHelpText('Ví dụ: B2105678. Dùng để xác nhận bạn là SV CTU, không hiển thị cho ai khác.')
    .setRequired(true);

  form.addTextItem()
    .setTitle('Email hoặc số Zalo để tụi mình liên hệ')
    .setHelpText('Chỉ dùng gửi link dùng thử, không spam.')
    .setRequired(true);

  // ══════════════════════════════════════════════════════════════
  // ĐẤU DÂY PHÂN NHÁNH (đặt sau cùng vì cần các trang đã tồn tại)
  // ══════════════════════════════════════════════════════════════

  // A1: "Có" → vào Phần A · "Không" → nộp luôn (loại khỏi mẫu)
  a1.setChoices([
    a1.createChoice('Có', trangA),
    a1.createChoice('Không', FormApp.PageNavigationType.SUBMIT)
  ]);

  // F1: "Có" → sang trang khai tên/MSSV · "Không" → nộp luôn
  f1.setChoices([
    f1.createChoice('Có, mình muốn dùng thử', trangFChiTiet),
    f1.createChoice('Không, mình chỉ tham gia khảo sát thôi', FormApp.PageNavigationType.SUBMIT)
  ]);

  // ══════════════════════════════════════════════════════════════
  Logger.log('✅ TẠO FORM XONG');
  Logger.log('LINK GỬI SV   : ' + form.getPublishedUrl());
  Logger.log('LINK CHỈNH SỬA: ' + form.getEditUrl());
  Logger.log('');
  Logger.log('CÒN 2 VIỆC LÀM TAY:');
  Logger.log('1. Bật "Xáo trộn thứ tự lựa chọn" cho câu B2, B4, E1');
  Logger.log('2. Kiểm tra lại danh sách Trường/Khoa ở câu A3 theo cơ cấu CTU hiện hành');
}
