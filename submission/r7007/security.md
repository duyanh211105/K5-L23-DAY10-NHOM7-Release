# Bảo mật khi làm việc

## 1. Ca USB: hết giờ, muốn chép lô về nhà làm tiếp
Khi hết giờ làm việc mà chưa hoàn thành nhiệm vụ, tuyệt đối không sao chép dữ liệu ra USB hay bất kỳ thiết bị lưu trữ cá nhân nào, không gửi file qua email cá nhân hay nhờ người ngoài làm hộ. Dữ liệu hình ảnh và nhãn gán là tài sản số được bảo vệ bởi thỏa thuận bảo mật NDA và chính sách an toàn thông tin của công ty. Việc đưa dữ liệu ra ngoài thiết bị công ty tiềm ẩn nguy cơ lộ lọt dữ liệu bí mật kinh doanh hoặc bị đánh cắp thông tin. Giải pháp đúng đắn là lưu lại tiến độ công việc trên hạ tầng nội bộ, báo cáo người quản lý để xin làm thêm giờ (overtime) tại văn phòng hoặc bàn giao lại công việc dở dang cho đồng nghiệp trong ca tiếp theo theo đúng quy trình.

## 2. Năm việc: được hay không
1. Mở job được giao trên máy công ty: ĐƯỢC. Đây là thiết bị làm việc chính thức được quản lý bảo mật bởi hệ thống CNTT của công ty, đúng phạm vi thẩm quyền được cấp phát.
2. Chụp màn hình gửi người quen: KHÔNG ĐƯỢC. Vi phạm nghiêm trọng thỏa thuận bảo mật dữ liệu và bí mật công nghệ, có thể gây rò rỉ hình ảnh dự án ra môi trường bên ngoài.
3. Chép lô ra USB: KHÔNG ĐƯỢC. Vi phạm quy định phòng chống thất thoát dữ liệu (DLP), thiết bị USB cá nhân tiềm ẩn nguy cơ lây nhiễm mã độc và dễ bị thất lạc dẫn đến mất an toàn dữ liệu.
4. Dán nhãn thật lên chatbot: KHÔNG ĐƯỢC. Các chatbot công cộng có thể lưu trữ prompt để đào tạo lại mô hình AI của họ, làm lộ lọt cấu trúc nhãn và thông tin nội bộ sang bên thứ ba.
5. Đưa tài khoản CVAT cho đồng nghiệp: KHÔNG ĐƯỢC. Vi phạm nguyên tắc bảo mật định danh và kiểm toán (Audit Trail). Mọi thao tác gán nhãn hay phê duyệt phải gắn với đúng trách nhiệm cá nhân, không được dùng chung thông tin đăng nhập.

## 3. Ca khuôn mặt: thấy mặt người rõ trong lô, guideline yêu cầu làm mờ
Khi phát hiện khuôn mặt người nhìn thấy rõ trong lô dữ liệu (ví dụ ảnh 000000023899 có 2 người đứng sát nhau nhìn rõ mặt, hoặc ảnh 000000012748 chụp người thẳng góc), hành động bắt buộc là đặt trạng thái lô dữ liệu là **HOLD** và báo cáo ngay lập tức cho người phụ trách dự án (Data Manager / Project Lead hoặc bộ phận Bảo vệ Dữ liệu Cá nhân). 
Tuyệt đối không tự ý dùng phần mềm đồ họa cá nhân để làm mờ hay tự ý xóa bỏ file ảnh. Lý do: Việc tự ý sửa pixel làm mờ sẽ làm thay đổi toàn bộ mã băm SHA-256 của file ảnh, phá vỡ tính toàn vẹn (integrity) của manifest và sai lệch hoàn toàn với mặt nạ phân đoạn panoptic đã gán tương ứng; việc xóa ảnh sẽ làm thiếu hụt file trong bộ dữ liệu đã chốt số lượng. Việc làm mờ khuôn mặt (bảo vệ quyền riêng tư PII theo chuẩn pháp lý) phải được xử lý tập trung thông qua pipeline tiền xử lý chuẩn của dự án và được phê duyệt chính thức bằng phiên bản dữ liệu mới.
