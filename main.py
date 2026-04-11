/* "또는" 텍스트 가림 해결 최종본 */
.separator-text {
    background-color: #0d0d0d; /* 다크모드 유리박스 느낌의 불투명한 배경색 */
    padding: 0 12px;
    position: relative;
    z-index: 1;
    transition: background-color 0.3s;
}

/* 라이트 모드일 때는 배경을 흰색으로 변경 */
body.light-mode .separator-text {
    background-color: #ffffff;
}
