class PermissionHandler:
    def __init__(self, config: dict):
        self.config = config["bilibili"]
        self.song_permission = self.config["song_request_permission"]
        self.next_permission = self.config["next_request_permission"]

    def is_allowed(self, request: dict) -> bool:
        user = request.get("user", {})
        req = request.get("request", {})
        req_type = req.get("type")

        # 如果是主播，永远允许
        if user.get("is_streamer", 0) == 1:
            return True

        # 选择对应权限配置
        if req_type == "song":
            perm = self.song_permission
        elif req_type == "next":
            perm = self.next_permission
        else:
            return False

        # 权限判断
        if perm.get("streamer", False) and user.get("is_streamer", 0) == 1:
            return True
        if perm.get("room_admin", False) and user.get("admin", 0) == 1:
            return True
        if perm.get("guard", False) and user.get("privilege_type", 0) > 0:
            return True
        if perm.get("medal_light", False) and user.get("medal_is_light", 0) == 1:
            return True
        if "medal_level" in perm:
            try:
                required = int(perm["medal_level"])
                if user.get("medal_level", 0) >= required:
                    return True
            except (ValueError, TypeError):
                pass
        return False
