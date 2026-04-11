        body { 
            font-family: 'Inter', sans-serif; 
            background-color: #000; 
            color: #fff; 
            transition: background-color 0.3s, color 0.3s;
            overflow: hidden; 
        }

        /* 라이트 모드 스타일 */
        body.light-mode {
            background-color: #ffffff;
            color: #000;
        }

        .glass-card {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.05);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.7);
            transition: all 0.3s;
        }

        /* 라이트 모드에서의 유리 박스 및 텍스트 설정 */
        body.light-mode .glass-card {
            background: rgba(0, 0, 0, 0.03);
            border: 1px solid rgba(0, 0, 0, 0.1);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.1);
        }
        body.light-mode .text-gray-400 { color: #666; }
        body.light-mode .input-field { background-color: #f5f5f5; border-color: #ddd; color: #000; }
        body.light-mode button.bg-white { background-color: #000; color: #fff; }

        .input-field {
            background-color: #1a1a1a;
            border: 1px solid #333;
            border-radius: 12px;
            transition: all 0.2s ease;
        }
        .input-field:focus { border-color: #555; outline: none; background-color: #222; }

        .btn-discord { background-color: #5865F2; transition: background-color 0.2s; }
        .btn-discord:hover { background-color: #4752C4; }

        .fade-in { animation: fadeIn 0.3s ease-in-out; }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(5px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .hidden { display: none; }
    </style>
