# Báo cáo kiểm chứng thực tế

## Cập nhật hỗ trợ Windows native / PowerShell

Thời điểm: 2026-10-20T21:02:10+07:00 (giờ Việt Nam).

README hiện hướng dẫn **Windows 10/11 x64, Python 3.12, Node 24, Geth 1.14.13 Windows amd64**.
Không cần Linux/WSL/Docker/Go để làm theo quy trình Windows. Người dùng tải và giải nén binary Geth chính thức;
installer nhận `-GethPath`, kiểm tra phiên bản rồi lưu đường dẫn local. Không dùng `/workspace` trong các entry point Windows.

Đã thực hiện:

- Kiểm tra cú pháp toàn bộ 5 script `.ps1` bằng parser PowerShell 7.4.6.
- Kiểm tra native argument có dấu cách và nonzero exit: helper giữ nguyên argument và dừng đúng khi lệnh ngoài trả exit 17.
- Chạy `install.ps1 -GethPath ...` bằng PowerShell 7.4.6 trên Linux: pip, npm ci, compile và 4 unit tests thành công.
- Chạy `start_geth.ps1`: khởi động Geth local thật, RPC loopback chain 1337.
- Chạy `demo.ps1`: swap một pool, ba pool, route và flash loan thành công.
- Chạy `verify_local.ps1`: **14 passed, 0 failed, 0 errors, 0 skipped**, thời gian 14.940 giây; xác nhận khôi phục biến RUN_INTEGRATION sau khi test.
- Tải thành công 47 wheels cho target CPython 3.12 Windows x64 / pure Python, gồm 45 package pin ban đầu và hai dependency Windows được bổ sung: `pywin32==311`, `colorama==0.4.6`.

**Chưa chạy trên Windows thật, chưa kiểm chứng Windows PowerShell 5.1 hoặc geth.exe.**
Chạy PowerShell 7 trên Linux và tải được Windows wheels không thay thế kiểm thử đầu-cuối trên Windows.
Script dùng cú pháp tương thích PowerShell 5.1, `py.exe -3.12`, `npm.cmd` và `.venv/Scripts/python.exe` khi ở Windows;
nhánh này vẫn cần được xác minh trên máy Windows của người dùng.

Máy cloud đã được khởi tạo lại trong phiên làm việc này: manifest cũ tồn tại nhưng bytecode cũ không có trên chain đang chạy.
CLI phát hiện và từ chối demo đúng cách; đã lưu bản sao manifest cũ trong `.local/` rồi deploy lại cả hai protocol để kiểm chứng tiếp.
Deployment mới: Aave Pool `0xBA137c60532E56cf8Bf119A83a51346D96389eE4`, receiver `0x3c81041669B5EB2413Bdbd0C2e692CfBE53b519b`.
Bằng chứng mới: `.local/install-powershell.log`, `geth-powershell.log`, `powershell-validation.log`, `test-results.xml`.
Không khẳng định snapshot cloud đã khôi phục đầy đủ trạng thái blockchain cũ.

---

Phần dưới lưu kết quả **lần kiểm chứng ban đầu**. Địa chỉ và số liệu trong phần lịch sử không nhất thiết trùng deployment mới.

Thời điểm chốt: 2026-10-20T20:27:22+07:00 (giờ Việt Nam). Kết quả từ **máy hiện tại**, Geth local chain **1337**, không phải Sepolia.

## Kết quả

| Yêu cầu | Kết quả đã thực hiện |
|---|---|
| 1. Kiến trúc Uniswap V2 | README, sơ đồ luồng và 30 câu hỏi vấn đáp kèm giải thích |
| 2. Deploy Uniswap trên Geth | Factory/Router chính thức, 4 token, WETH9, hai market, năm Pair |
| 3. CLI Python token/token và multi-pool | Giao dịch A→B và A→B→C→D thành công, output bằng quote |
| 4. Tìm route | DFS theo exact-input, reserve snapshot cùng block; quote khớp Router và thực thi thành công |
| 5. Deploy Aave thử nghiệm | Aave V3 core thật, Provider/proxy/ACL/libraries/reserve A; supply 1.000.000 A |
| 6. Flash loan Aave + Uniswap | Vay 100 A, hai swap, trả đủ gốc+phí; profit và rollback đã kiểm thử |

`bash scripts/install.sh` đã chạy thành công, gồm cài dependencies theo lockfile, compile Solidity, tái sử dụng Geth đúng phiên bản và chạy unit tests.
Geth được build từ release v1.14.13 bằng Go 1.23.6; archive Go kiểm SHA256 từ metadata chính thức và Go checksum database được giữ bật.
Cài Geth từ module registry thuần hoặc nguồn binary ban đầu bị chặn bởi egress; registry có fallback Git trực tiếp đã build thành công, không tắt xác minh.
Solidity dùng 0.8.19, viaIR + optimizer, EVM Paris; Python 3.12.14, web3 7.14.0, Node 24.19.0.

## Kiểm thử

Lệnh: `bash scripts/verify_local.sh`.

**14 passed, 0 failed, 0 errors, 0 skipped**, gồm 4 unit tests và 10 integration tests. Thời gian runner: 17.123 giây.
Có một cảnh báo deprecation từ websockets dependency; không có lỗi test.

Integration tests đã kiểm:

- Node Geth thật, bytecode, aToken và số dư thanh khoản Aave.
- Swap một pool và invariant tích reserves không giảm.
- Swap ba pool với đúng ba Swap event, số dư output khớp quote.
- Best route cho nhiều output hơn A→D trực tiếp và quote khớp Router tại cùng block.
- Flash loan có profit; aToken nhận lại gốc cùng đúng premium 5 bps.
- Giao dịch không đạt minProfit revert; reserves, receiver balance và số dư A ở aToken không đổi, kể cả receiver đã có tiền nạp trước.
- Callback trái phép, deadline hết hạn và minOut quá cao đều revert bằng giao dịch đã mine.
- Ký giao dịch Python bằng ví local sinh trong bộ nhớ; owner guard từ chối ví khác.
- Vay vượt thanh khoản Aave revert.

Receipt ledger qua `Chain.send`: 78 giao dịch, 72 status=1 và 6 status=0 cố ý trong failure tests.
Giao dịch ETH cấp gas cho ví test được gửi trực tiếp qua web3 và kiểm receipt riêng, không nằm trong ledger này.
Không coi receipt revert mong đợi là lỗi suite; không dùng eth_call thay cho bằng chứng giao dịch đã mine.

## Một số số liệu demo

| Thao tác | Kết quả | Transaction hash local |
|---|---|---|
| 10 A → B | 9.969006090092817746 B | `0x416354c1e354e5f9cc5c5f10161a37e1bd069b6ed6a67eee011c2132e3dd21af` |
| 10 A → B → C → D | 9.905337629545614499 D | `0x931d9d566b5f648f240801fbdc1e373f3007b54b66d4b1f8206ba8d61f6abb19` |
| Flash loan 100 A | premium 0.05 A; profit 18.851763888035240019 A | `0x023ae407b479226083801ebd4a7197d4cb52eb037bc99c845158995aeebc3cb7` |
| Swap 1 A sau restart | 0.991241211579699463 B | `0xfcee1ee3e2b7faf358a335395ee05bd46747f3d6fb7f5a243bcd7213a099a3bc` |

Profit nêu trên **chưa trừ gas ETH** và đến từ chênh lệch reserves được chủ động seed cho bài học.
Các giao dịch sau làm thay đổi reserves nên kết quả lần chạy sau sẽ khác.

## Deployment trong lần kiểm chứng ban đầu

| Thành phần | Địa chỉ local |
|---|---|
| Main Factory | `0xb6f3275988f642FEE1078773017448EcFa90b4c8` |
| Main Router | `0x5F597d6DDA28F9f7205c7db078c8BE493657BaE5` |
| Aave Provider | `0xf5CC1b2883d5051a6316819330057BEaCf96d89a` |
| Aave Pool proxy | `0x0DBeD506A4FF315EdAA4167aC588431a753aB09e` |
| FlashArbitrage | `0xf7Dd5d86e3d515975f6047Db29d92b1666811d44` |

Geth đã nhận SIGINT, flush state và dừng sạch. Sau khởi động lại, log xác nhận load block 267 từ đĩa, cùng dev account;
manifest/bytecode còn nguyên, reserve query và giao dịch swap mới ở block 297 thành công.
Node được để chạy cho buổi demo. Không cần deploy lại khi dùng trạng thái local hiện tại.

## Bằng chứng trong workspace

Các tệp dưới `.local/` được gitignore vì gắn với một chain cụ thể:

- `install.log`, `deploy-uniswap.log`, `deploy-aave.log`: cài đặt và deploy.
- `swap-single.json`, `swap-multi.json`, `route.json`, `demo.log`: kết quả CLI.
- `tests.log`, `test-results.xml`: kết quả runner lần kiểm chứng này.
- `transactions-1337.jsonl`: hash, block, receipt status và gas.
- `geth.log`, `geth-restart.log`, `restart-status.json`, `restart-route.json`, `restart-swap.json`: lưu/khôi phục trạng thái và readiness.
- `deployment-1337.json`: toàn bộ địa chỉ và chain/genesis identity.

## Phạm vi chưa kiểm chứng

- **Sepolia chưa chạy:** chưa có RPC/ví testnet được cấu hình. Có đường deploy và ký giao dịch Python, nhưng không có receipt Sepolia và không khẳng định đã deploy testnet.
- Aave là market tối thiểu một reserve, fixed-price oracle dành cho lab. Chưa cấu hình/kiểm thử collateral borrowing, liquidation, governance, production oracle.
- Routing chỉ main Factory, simple path trong hop bound, tối đa output trước gas. Chưa có split route, gas-aware routing hay MEV protection.
- Chưa xác minh restoration trong một cloud task mới; kiểm chứng hiện tại là restart Geth trên cùng máy.
- Deploy nhiều transaction chưa resume theo từng bước; nếu dở dang do hết gas, contract đã mine vẫn tồn tại và có thể cần deploy market mới.

## Cấu hình môi trường đã lưu

Đã lưu bản nháp hai trường **install_script** và **start_skill**; giữ nguyên repository/network/secret settings.
Start instructions dùng checkout hiện có, không tạo worktree, khởi động lại Geth và kiểm tra manifest/route.
Đây là lưu bản nháp, **chưa publish**: người dùng xem/lưu trong Environment settings, sau đó Publish để chụp trạng thái dùng cho phiên mới.
