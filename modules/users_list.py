class UsersList(dict):
    def __setitem__(self, key, value):
        if self[key]:
            return None
        super().__setitem__(key, value)

    def __getitem__(self, item):
        return super().get(item)


users_list = UsersList()
