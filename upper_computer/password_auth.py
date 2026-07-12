# password_auth.py
from config import DOOR_PASSWORD, ADMIN_PASSWORD

class PasswordManager:
    def __init__(self):
        self.door_password = DOOR_PASSWORD
        self.admin_password = ADMIN_PASSWORD

    def check_door_password(self, pwd):
        return pwd == self.door_password

    def check_admin_password(self, pwd):
        return pwd == self.admin_password

    def change_door_password(self, old_pwd, new_pwd):
        if old_pwd == self.door_password:
            self.door_password = new_pwd
            return True
        return False

    def change_admin_password(self, old_pwd, new_pwd):
        if old_pwd == self.admin_password:
            self.admin_password = new_pwd
            return True
        return False