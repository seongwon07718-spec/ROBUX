    if not result.get("purchased"):
        reason = (
            result.get("reason")
            or result.get("errorMsg")
            or "구매 조건이 맞지 않습니다."
        )
        # ✅ Success도 성공으로 처리
        if reason == "Success":
            pass  # 아래 성공 처리로 넘어감
        else:
            return {"success": False, "message": reason}
