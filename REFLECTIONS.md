# Reflections

## 1) Multi-account
Nếu chạy costctl cho 100 tài khoản, em sẽ dùng cross-account IAM role và AssumeRole theo danh sách account. Mỗi account chạy list/cost riêng, rồi gom kết quả về một CSV theo từng account và tổng hợp thêm một bảng tổng. Có thể dùng AWS Organizations để lấy danh sách account và chạy song song bằng threads/async để giảm thời gian.

## 2) idle vs Trusted Advisor
`idle` dùng CPU 24h nên phù hợp khi cần quyết nhanh cho môi trường dev/test ngắn hạn. Trusted Advisor dùng 14 ngày nên chính xác hơn cho môi trường sản xuất, tránh false positive. Em sẽ tin Trusted Advisor hơn cho prod, còn `idle` để dọn dẹp nhanh tài nguyên thử nghiệm.

## 3) clean --apply blast radius
Em sẽ muốn có ít nhất 3 lớp bảo vệ: tag bắt buộc kèm owner/team, dry-run bắt buộc, và allow-list theo account/env. Ngoài ra nên bật termination protection, thêm policy chặn delete khi tag không khớp, và log lại mọi hành động để audit. Nếu lỡ chạy nhầm, cần có backup/snapshot tự động để rollback.

## 4) AI assistance
Ước lượng khoảng 60% code ban đầu lấy từ AI, nhưng em đã chỉnh sửa để đúng theo test/spec, sửa format output và thêm logic kiểm tra. Phần em tự sửa nhiều nhất là luồng xử lý S3 tags và các output theo yêu cầu của tests.

## 5) W7 carry-over
Em sẽ giữ `list`, `cost`, `terminate`, `tag` vì dùng thường xuyên khi vận hành nhiều account. Em có thể bỏ `idle` và `migrate-gp3` nếu không còn nhu cầu tối ưu chi phí theo từng instance/volume, hoặc thay bằng report tập trung theo account.
