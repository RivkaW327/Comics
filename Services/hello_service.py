from ..Repositories.hello_repository import HelloRepository

class HelloService:
    @staticmethod
    def say_hello(name: str):
        return HelloRepository.get_hello_message(name)