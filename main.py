/* 이 코드를 복사해서 넣으세요 */
.separator-container {
    display: flex;
    align-items: center;
    text-align: center;
    color: #666; 
    font-size: 0.75rem;
    margin: 20px 0; /* 위아래 간격 추가 */
}

.separator-container::before,
.separator-container::after {
    content: '';
    flex: 1;
    border-bottom: 1px solid #333; /* 선 색상 */
}

.separator-container::before { margin-right: 15px; }
.separator-container::after { margin-left: 15px; }

/* 라이트 모드일 때 선 색상 변경 */
body.light-mode .separator-container::before,
body.light-mode .separator-container::after {
    border-bottom: 1px solid #ddd;
}
