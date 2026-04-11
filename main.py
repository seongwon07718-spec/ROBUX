body.light-mode {
    background-color: #ffffff;
    color: #000;
}

/* 추가할 코드 */
.separator-text {
    background-color: #080808; /* 유리박스 뒤 선을 가릴 불투명한 배경색 */
    padding: 0 12px;
    position: relative;
    z-index: 1;
}
body.light-mode .separator-text {
    background-color: #ffffff; /* 라이트모드일 땐 흰색으로 선을 가림 */
}
