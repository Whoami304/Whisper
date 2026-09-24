import os
from PIL import Image
from stegano import lsb


class StegoError(Exception):
    """დაშიფრვის/გაშიფრვის შეცდომა. იგზავნება მაშინ, როცა ოპერაცია ვერ შესრულდა."""


""" გადავწყვიტე ყველა შვილობილ კლასს თავისი ფუნქციონალი მივანიჭო, ყველა ეს კლასი სთავესც იღებს class Steganography-ის გან
     ,შემგდომ მოდის   TextSteganography, რომელშიც უშუალოდ ტექსტის ფოტოში ჩამალვის ფუნქციონალი აკისრია და ასე გაგრზელდება 
     იქამდე სანამ პუ არ დააკმყოფილებს ყველაც საჭირო მოთხოვნასა და ფუნქციონალს, ეს არის ოოპში სწორი მიდგომა,რიტიც კოდიბ ხდება
      უფრო მარტივად აღსაქმელი და წაკითხვადი.  
"""

class Steganography:
    def __init__(self):
        pass

    def Check_Content(self):
        pass


class TextSteganography(Steganography):
    def __init__(self):
        self.img_path = ''
        self.secret_message = ''
        self.output_img = ''

    def Cheak_Content(self,img_path):

        """ეს არის მეთოდი რომერლიც იღებს არგუმენტად ფოტოს და ამოწმებს შეიცავს თუ არა კონტენტს
           თუმცა ხდება კონტენტის ამორება, რამაც შეიზლება საფრტხე შეუქმნას უსაფრტხოებას, რადგან არის ალბატობა
           რომ კომტენტმა გაჯონოს. ამ საშისროების პრევენციის მიზნით კონტენტი არსად ინახება და არ იბეჭდება.
           ერთადერთი იგი ინახება მხოლოდ სტრიქონსიო, რომლის სიგრზეც მოწმდება და დგინდება შეიცავს თუ არა იგი კონტენტს.ძ
        """
        self.img_path = img_path
        try:
            if not os.path.exists(self.img_path):
                return False
            hide_content = lsb.reveal(self.img_path)
            check_size = lambda hide_content : hide_content and len(hide_content) > 0
            return bool(check_size(hide_content))
        except Exception:
            # ფოტო ან დაზიანებულია, ან საერთოდ არ შეიცავს დამალულ ტექსტს.
            # შეცდომის ტექსტი აქ არ ბრუნდება, რადგან გამომძახებელი პასუხს bool-ად კითხულობს
            # და ნებისმიერი არაცარიელი სტრიქონი "ნაპოვნია"-დ ითვლებოდა.
            return False

    # ბაზისურ კლასში მეთოდს Check_Content ჰქვია; ორივე სახელი მუშაობს.
    def Check_Content(self, img_path):
        return self.Cheak_Content(img_path)

    def set_parameters(self,img_path,secret_message,output_img):
        self.img_path = img_path
        self.secret_message = secret_message
        self.output_img = output_img
        return "Done"


    @staticmethod
    def capacity_bits(img_path: str) -> int:
        """ფოტოში ხელმისაწვდომი ბიტების რაოდენობა (თითო არხზე თითო ბიტი)."""
        with Image.open(img_path) as img:
            width, height = img.size
        return width * height * 3

    @staticmethod
    def required_bits(secret_message: str) -> int:
        """
        ბიტების რაოდენობა, რომელსაც stegano რეალურად ჩაწერს: ჯერ მოდის
        "<ბაიტების რაოდენობა>:" პრეფიქსი, შემდეგ თავად ტექსტი UTF-8-ში,
        ბოლოს კი ივსება სამის ჯერადამდე (თითო პიქსელი სამ ბიტს იტევს).
        """
        message_bytes = secret_message.encode("utf-8")
        prefix_bytes = (str(len(message_bytes)) + ":").encode("ascii")
        bits = (len(prefix_bytes) + len(message_bytes)) * 8
        return bits + ((3 - (bits % 3)) % 3)

    def encode_info(self, img_path: str, secret_message: str, output_img: str) -> str:
        """
        დაშიფრის მეთოდი, იღებს სამ პარამეტრს,დასამალ შეტყობინებას, შემავალ და გამომავალ ფოტოს.
        წარმატებისას აბრუნებს შეტყობინებას, წარუმატებლობისას კი აგდებს StegoError-ს,
        რომ გამომძახებელმა შეცდომა ვერ გამოტოვოს.
        """
        self.set_parameters(img_path, secret_message, output_img)

        if not isinstance(secret_message, str):
            raise StegoError("Secret message must be a string.")
        if secret_message == "":
            # stegano ცარიელ ტექსტს assert-ით აგდებს, რაც -O რეჟიმში საერთოდ არ მუშაობს
            raise StegoError("Secret message is empty, there is nothing to hide.")
        if not os.path.exists(self.img_path):  # მოწმდება ფაილის არსებობა
            raise StegoError(f"Image file not found: {self.img_path}")

        try:
            capacity = self.capacity_bits(self.img_path)
        except Exception as e:
            raise StegoError(f"Carrier image could not be read: {e}")

        required = self.required_bits(secret_message)
        if required > capacity:
            raise StegoError(
                f"Message is too large for this image: needs {required} bits, "
                f"image holds {capacity} bits."
            )

        try:
            # auto_convert_rgb=True აუცილებელია: მის გარეშე stegano არა-RGB ფოტოზე
            # input()-ით ითხოვს დადასტურებას და GUI სამუდამოდ იჭედება.
            secret_image = lsb.hide(self.img_path, self.secret_message, auto_convert_rgb=True)
            secret_image.save(self.output_img)  # ინახასვს დამალიულ ფაილს
        except Exception as e:
            raise StegoError(f"Encoding error: {e}")
        return f"Message successfully hidden in: {self.output_img}"

    def decode_info(self, img_path: str):
        """
        ერთპარამეტრიანი მეტოდი, რომელის პასუხისმგერბელია დეკოდზე.
        აბრუნებს დამალულ ტექსტს, ან None-ს თუ ტექსტი არ მოიძებნა.
        შეცდომის ტექსტი აღარ ბრუნდება, რადგან გამომძახებელი მას დამალულ
        შეტყობინებად აღიქვამდა და შემდეგ გაშიფრვას ცდილობდა.
        """
        self.img_path = img_path
        if not os.path.exists(self.img_path):
            return None
        try:
            return lsb.reveal(self.img_path) or None
        except Exception:
            return None

    # def convert_to_Png(self, img_path: str) -> str:
    #     try:
    #         img = Image.open(img_path)
    #         new_path = os.path.splitext(img_path)[0] + ".png"
    #         img.save(new_path, "PNG")
    #         return new_path
    #     except Exception as e:
    #         return f"Conversion error: {e}"

    def read_from_file(self, file_name: str) -> str:
        """
        Read text content from a file.
        """
        try:
            with open(file_name, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return "File not found."



