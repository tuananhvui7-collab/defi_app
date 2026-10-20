# Câu hỏi vấn đáp DeFi Lab 4

1. **Factory, Pair và Router khác nhau thế nào?** Factory tạo và liệt kê Pair. Pair giữ token, phát hành LP token và kiểm invariant. Router phối hợp transfer, quote, đường đi, deadline và minOut; logic bảo toàn tài sản nằm ở Pair.
2. **Tại sao phải approve?** ERC20 không cho Router tùy ý lấy tiền của người dùng. `approve` cấp allowance, Router gọi `transferFrom`. Approve không tự swap. Cho allowance vô hạn tiện cho seed lab nhưng tạo rủi ro nếu spender không đáng tin.
3. **Giải thích công thức output.** Phí chỉ cho 997/1000 input tác động vào đường cong. Giải phương trình constant-product cho output rồi làm tròn xuống. Trong code: `dx*997*y // (x*1000 + dx*997)`.
4. **Có phải k luôn bằng hằng số?** Mô hình lý tưởng không phí có k cố định. Với phí, số dư thực sau swap làm tích reserves thường tăng; Pair kiểm adjusted balances để đảm bảo không lấy quá nhiều output.
5. **token0 là gì?** Token có địa chỉ nhỏ hơn theo thứ tự số. Tên A/B không quyết định token0. Đảo reserves sai sẽ tính sai quote; xem `snapshot_graph`.
6. **Tại sao swap nhiều pool là atomic?** Router gọi các Pair trong cùng transaction EVM. Một call revert làm hoàn tác toàn bộ thay đổi bên trong; phí gas của transaction thất bại vẫn phải trả.
7. **Token B và C đi đâu trong A→B→C→D?** Pair đầu chuyển B vào Pair tiếp theo, Pair giữa chuyển C vào Pair cuối. Ví nhận D; không cần ba giao dịch hay approve B/C của người dùng.
8. **Slippage và price impact khác nhau thế nào?** Price impact là biến động giá do chính kích thước lệnh trên đường cong. Slippage là chênh giữa quote và lúc thực thi, gồm thay đổi trạng thái bởi người khác. `minOut` không loại bỏ price impact.
9. **Deadline có chống MEV không?** Nó chỉ giới hạn thời gian hợp lệ. MinOut và deadline không loại bỏ sandwich; route lab chưa giải bài toán MEV hay private relay.
10. **Tại sao không chọn ít hop nhất?** Ít phí hơn có thể tốt nhưng pool trực tiếp có giá/thanh khoản xấu hơn. Lab cố ý tạo A/D kém hơn ba hop. Phải tính output theo amount và reserves thực.
11. **Tại sao không Dijkstra với -log spot price?** Với giao dịch có kích thước đáng kể, trọng số phụ thuộc input và thay đổi theo amount đi qua cạnh. Spot price bỏ qua price impact. DFS bounded mô phỏng exact-input từng hop phù hợp đồ thị nhỏ.
12. **Thuật toán có thật sự tối ưu?** Tối đa output trước gas trong các simple path của main Factory, không quá max_hops. Không tối ưu mọi DEX, split route, chu trình hay lợi nhuận sau gas. Độ phức tạp tăng theo hàm mũ của hop bound.
13. **Tại sao đọc reserves cùng một block?** Tránh ghép trạng thái các pool tại những thời điểm không nhất quán. Dù vậy, quote là snapshot, không đảm bảo reserves tại lúc mine; phải dùng minOut.
14. **Aave Pool có phải mock không?** Không. Lab deploy artifact Aave V3 chính thức, link library, tạo proxy qua Provider, cấu hình reserve và supply thật. Chỉ token và fixed-price oracle là dành cho lab. Không có toàn bộ cấu hình của market production.
15. **Provider, Configurator, ACL có vai trò gì?** Provider giữ địa chỉ thành phần và tạo proxy; Configurator cấu hình reserve/premium theo role; ACLManager xác định quyền quản trị. Admin lab có quyền lớn nên không tương đương governance production.
16. **aToken khác LP token thế nào?** aToken biểu diễn khoản supply vào lending pool, số dư/giá trị tăng theo liquidity index. LP token Uniswap biểu diễn phần sở hữu hai tài sản của AMM và chịu impermanent loss. Stable/variable debt token ghi nhận nợ, không phải tiền người dùng có thể swap như ERC20 thường.
17. **Flash loan có cần thế chấp không?** Không nếu gốc+phí được trả trong cùng transaction. EVM atomicity bảo đảm lender có thể revert toàn bộ nếu điều kiện không đạt, thay cho thế chấp qua nhiều block.
18. **Callback nào được gọi và ai được gọi?** Aave Pool gọi `executeOperation`. Receiver phải kiểm tra cả Pool và initiator; nếu chỉ kiểm Pool, kẻ khác có thể yêu cầu Pool gọi receiver ngoài ý muốn. Lab còn kiểm tra trạng thái active.
19. **Trả tiền bằng cách nào?** Receiver approve Pool số gốc+premium; sau callback trả true, Pool transferFrom để thu lại vào aToken. Chỉ trả true mà không đủ balance/allowance sẽ thất bại.
20. **Vay 100 A với phí 5 bps trả bao nhiêu?** 100,05 A; phí 0,05 A. Aave PercentageMath có rounding theo số nguyên; Python dùng `(amount*bps + 5000)//10000`. Không hardcode giả định mọi Aave market đều có cùng fee; đọc premium on-chain.
21. **Tại sao có hai Router?** Hai Factory có các Pair độc lập với tỷ lệ reserves khác nhau. Mua B ở market 1 rồi đổi B lấy A ở market 2 có thể lời. Nếu quay lại cùng Pair ngay, phí và price impact thường làm lỗ.
22. **Profit được tính thế nào?** `finalBalance - initialBalance - principal - premium` trong callback; sau Pool thu tiền, phần tăng balance receiver phải bằng profit event. Tài sản có sẵn không được bù vào phép kiểm tra lợi nhuận.
23. **Arbitrage có lãi token nghĩa là có lãi kinh tế không?** Chưa. Phải quy đổi gas ETH, tính khả năng fail, MEV và chi phí vận hành. Lab kiểm lợi nhuận bằng token A và báo gas_used, chưa trừ gas ra A.
24. **Bằng chứng flash loan thành công là gì?** Receipt status 1, event amount/premium/profit đúng, balance receiver tăng đúng profit và balance tài sản A ở aToken tăng đúng premium. Một hash hoặc log Python chưa đủ.
25. **Bằng chứng rollback là gì?** Gửi giao dịch có minProfit không thể đạt, nhận receipt status 0; so sánh reserves của cả hai DEX, balance receiver và balance aToken trước/sau bằng nhau. Chỉ eth_call revert chưa chứng minh đã mine một giao dịch thất bại.
26. **Tại sao prefund receiver khi test thất bại?** Để bắt lỗi tính lợi nhuận bằng tổng balance: receiver dù có sẵn 5.000 A vẫn phải revert nếu giao dịch mới không tạo đủ profit. Không được dùng tiền có sẵn để che lỗ.
27. **Geth --dev có phải testnet công khai không?** Không, là blockchain riêng disposable với tài khoản dev được cấp ETH và auto-mining. Nó kiểm thực thi EVM và giao dịch thật trong chain riêng, chưa kiểm latency, public mempool hay hạ tầng Sepolia.
28. **Muốn chạy Sepolia cần thay gì?** RPC, chain ID 11155111, ví chỉ testnet có gas; dùng signed transactions. Không mang địa chỉ deployment từ local sang. Manifest theo chain; phải deploy hoặc cung cấp địa chỉ đã được xác minh của đúng chain.
29. **Vì sao không dùng Python cho smart contract/Geth?** Python chạy off-chain, không thể thay EVM bytecode của giao thức. Solidity biên dịch ra bytecode on-chain. Geth là client Go có sẵn; lab không yêu cầu viết Go. Có thể dùng RPC testnet để khỏi cài Geth.
30. **Giới hạn bảo mật và phạm vi bài này?** Token mintable và oracle fixed-price chỉ phục vụ lab; admin tập trung; chưa audit, chưa test liquidation/regular borrowing/governance, chưa MEV/gas-aware routing. Chỉ local/testnet, không sử dụng tiền thật.

## Thực hành khi vấn đáp

- Mở `amount_out`, tính tay ví dụ 1.000 input với reserves 10.000/10.000: output 906 đơn vị.
- Mở `execute_swap`, chỉ ra approve, quote, minOut, deadline và balance delta.
- Mở `best_route`, giải thích tại sao token/Pair không bị lặp và bound 3 hop bao phủ A/B/C/D.
- Mở `executeOperation`, chỉ ra kiểm caller/initiator và công thức bảo vệ balance ban đầu.
- Chạy suite tích hợp và đọc cả receipt thành công lẫn receipt revert; đối chiếu file báo cáo kiểm chứng.
