class HelloRepository:
    @staticmethod
    def get_hello_message(name: str):
        return {"message": f"Hello {name}"}