# Bảo mật khi làm việc

> Áp dụng cho lô `lab250_20c5f74a77e2` (seed 7007) nhóm vừa QC và bàn giao — 250 ảnh COCO val2017, trong đó có nhiều ảnh chụp người thật.

## 1. Ca USB: hết giờ, muốn chép lô về nhà làm tiếp

Không chép lô ra USB hay bất kỳ thiết bị cá nhân nào, cũng không gửi file về email cá nhân. Điều này khiến dữ liệu đã ký NDA ra khỏi môi trường được kiểm soát của công ty: USB cá nhân dễ thất lạc, dính mã độc, và một khi dữ liệu rời hạ tầng nội bộ thì không còn audit trail nào cho biết nó đi đâu.

Cách làm đúng: lưu tiến độ vào nội bộ  báo quản lý trực tiếp để xin ở lại làm thêm giờ hoặc chuyển phần dở sang ca sau cho đồng nghiệp tiếp tục theo đúng quy trình bàn giao. Nếu hạn cả đêm là thật thì để quản lý quyết định.

## 2. Năm việc: được hay không

1. **Mở job được giao trên máy công ty — ĐƯỢC.** Đây đúng phạm vi quyền đã được cấp: tài khoản của bạn gắn với job đó, máy công ty có DLP và logging, mọi thao tác đều truy vết được về đúng người.
2. **Chụp màn hình gửi người quen — KHÔNG.** Ảnh chụp vẫn là dữ liệu dự án (ảnh có người thật, nhãn, guideline nội bộ); gửi ra ngoài qua kênh cá nhân là rò rỉ dữ liệu bất chấp dữ liệu gốc có được chép ra hay không, và không cách nào thu hồi lại được.
3. **Chép lô ra USB — KHÔNG.** Vấn đề ở mục 1: dữ liệu rời môi trường kiểm soát, thiết bị thất lạc được, không audit trail.
4. **Dán nhãn thật lên chatbot — KHÔNG.** Chatbot công khai có thể lưu hội thoại để huấn luyện hay cải tiến dịch vụ; nhãn và guideline là tài sản của dự án, và với lô có ảnh người thật thì còn dính dữ liệu cá nhân.
5. **Đưa tài khoản CVAT cho đồng nghiệp — KHÔNG.** Tài khoản là định danh cá nhân: mọi dòng gán nhãn hay phê duyệt trong CVAT phải truy về đúng người chịu trách nhiệm. Cho mượn tài khoản làm hỏng audit trail — ảnh bị gán sai sẽ không biết tìm ai, và chính bạn vẫn chịu trách nhiệm cho mọi thao tác xảy ra dưới tên mình. Đồng nghiệp cần quyền thì xin cấp tài khoản riêng.

## 3. Ca khuôn mặt: thấy mặt người rõ trong lô, guideline yêu cầu làm mờ

Trong lô có ảnh khuôn mặt nhìn rất rõ — ví dụ `000000023899` (người phụ nữ tóc ngắn ngồi trên sofa, người xem ảnh nhóm này đã xác nhận rõ nhân dạng) và `000000012748` (người áo đỏ bế em bé, chụp gần đối diện). Khi phát hiện, việc đúng là: **đặt lô về trạng thái HOLD** (dừng phát hành, không cho lô đi tiếp vào train hay lưu trữ ngoài), **báo ngay người phụ trách dữ liệu** (Data Manager / Project Lead / bộ phận bảo vệ dữ liệu cá nhân) kèm danh sách ảnh cụ thể, rồi chờ quyết định xử lý tập trung.

Không tự ý mở Photoshop làm mờ hay xóa file, vì ba lý do: (1) sửa pixel làm thay đổi SHA-256 của ảnh — manifest và `.sha256` vừa đóng gói lập tức sai lệch, phá vỡ tính toàn vẹn mà Pha 4 mới chứng minh xong; (2) xóa ảnh làm hụt số lượng 250 ảnh đã chốt và mất luôn cả nhãn panoptic tương ứng; (3) làm mờ khuôn mặt là xử lý dữ liệu cá nhân theo yêu cầu pháp lý — phải chạy qua pipeline chuẩn của dự án, có phê duyệt và phát hành thành phiên bản dữ liệu mới (ghi lineage), chứ không phải thao tác tay của người gán nhãn.
