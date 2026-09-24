import hashlib
import string
from random import choice

# ცეზარის შიფრის სიგრძე ყოველთვის ლუწია და 2-16 შუალედშია
SHIFT_CHOICES = [i for i in range(2, 17) if i % 2 == 0]


class Protection:
    def __init__(self):
        pass
class PasswordProtection(Protection):
    def __init__(self):
        self.shift = choice(SHIFT_CHOICES) # ნაგულისხმევი სიგრძე, როცა პაროლი არ არის ცნობილი
        self.alphabet = string.ascii_letters + string.digits + string.punctuation # სტრინგ მოდულიდან ამოღებული სტრიქონების
        #კონკატენაცია ხდება, რათა შიფრმა დაურბინოს და ნახოს და ჩაანაცვლოს სიმბოლო სესაბამის ბოზიციაზე, ხდება სიმბოლოების,ციფრების
        # და ასკი სიმბოლოების კონკატენაცია

    def shift_for(self, password: str) -> int:
        """
        პაროლიდან დეტერმინისტულად იღებს ცეზარის შიფრის სიგრძეს.

        self.shift რანდომადაა დაგენერირებული და ყოველ გაშვებაზე იცვლება, ამიტომ
        დაშიფრვა და გაშიფრვა სხვადასხვა პროცესში სხვადასხვა სიგრძეს იყენებდა და
        შედეგად ტექსტი ჩუმად ზიანდებოდა. სიგრძე პაროლზეა მიბმული, რომ ერთი და იგივე
        პაროლი ყოველთვის ერთსა და იმავე შედეგს იძლეოდეს.
        """
        digest = hashlib.sha256(password.encode("utf-8")).digest()
        return SHIFT_CHOICES[digest[0] % len(SHIFT_CHOICES)]

    def check_complexity(self, password: str) -> bool:
        """
        ეს არის მეთოდი,რომელიც ამოწმებს პაროლის სირტულეს შემდეგი პრინციპით:
        მოწმდება არის თუ არა პაროლი ციფრებს და სპეცსიმბოლოებს და ბრუნდება პასუხი ამ სიმბოლოების სახით

          """

        has_punct = any(c in string.punctuation for c in password)
        has_digit_1_to_9 = any(c in "0123456789" for c in password)
        return has_punct and has_digit_1_to_9

    def generate_password(self):
        """აქ ხდება პაროლისც გენერაცია 8-17 სიგრძის შუალედში,ვიძახებთ მეთოდს  check_complexity, რომელსაც გადავცემთ დაგენერირებულ
         პაროლს,რათა შეამოწმოს აკმაყოფილებს თუ არა პაროლი მოცემულ პირობებს.
        """

        length = choice([i for i in range(8, 17) if i % 2 == 0])
        while True:
            candidate = ''.join(choice(self.alphabet) for _ in range(length))
            if self.check_complexity(candidate):
                return candidate

    # def process_password(self, user_password: str) -> str:
    #     target_length = choice([i for i in range(8, 17) if i % 2 == 0])

    #     """ აქ ხდება მომხმარებლის მიერ შეტანილი პაროლის სიგრძის შედარება რეკომენდირებული პაროლის სიგრზესტან,
    #     თუ მომხმარების პაროლის უფრო მეტი სიგრძისაა,ან ტოლია და ნაკლებია ან ტოლია, მაშინ პაროლის სიგრზე მისაღებია,
    #      თუ მეტია რეკომედირებულზე, მაშინ ვტოვებთ და მომხმარებელს ვეუბნებით რომ პაროლი რთულია დასამახსოვრებელია, სხვა შემთხვევაში პაროლია სუსტია
    #       და ვაგენერირებთ ჩვენიით  """

    #     if len(user_password) >= target_length and len(user_password) <= 16:
    #         print(f"Your password has \"{user_password}\" good length and can be used.")
    #         return user_password

    #     elif len(user_password) > 16:
    #         print(f"Your password \"{user_password}\" is strong but too long to remember easily.")

    #         return user_password

    #     else:
    #         print(f"Your password \"{user_password}\" is too weak. \n..Generating a new strong password...")
    #         new_pass = self.generate_password()
    #         print(f"[INFO]  New Password - {new_pass}")
    #         return new_pass


    def process_password(self, user_password: str) -> tuple:
        target_length = choice([i for i in range(8, 17) if i % 2 == 0])

        # პაროლი არსად ჩნდება შეტყობინებაში, რომ ის შემთხვევით არ გამოჩნდეს ეკრანზე ან ლოგში
        if len(user_password) >= target_length and len(user_password) <= 16:
            message = "Your password has a good length and can be used."
            return user_password, message

        elif len(user_password) > 16:
            message = "Your password is strong but too long to remember easily."
            return user_password, message

        else:
            message = "Your password is too weak.\n..Generating a new strong password..."
            new_pass = self.generate_password()
            return new_pass, message


