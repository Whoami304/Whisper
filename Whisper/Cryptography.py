# import string

# from protection import *
# from string import *

# class Crypography:
#     def __init__(self):
#         pass


# class CaserCipher(Crypography):
#       def __init__(self):
#          self.password = ""

#          self.AllSybols = string.printable


#       def Encrypt(self, text, shift):
#           self.text = text
#           self.shift = shift






import string

# Assuming 'protection' module is in the same directory
from protection import *

class Crypography:
    def __init__(self):
        pass


class CaserCipher(Crypography):
    def __init__(self):
        self.password = ""
        self.AllSybols = string.printable

    def Encrypt(self, text, shift):
        self.text = text
        self.shift = shift
        encrypted_text = ""
        for char in text:
            if char in self.AllSybols:
                old_index = self.AllSybols.find(char)
                new_index = (old_index + self.shift) % len(self.AllSybols)
                encrypted_text += self.AllSybols[new_index]
            else:
                encrypted_text += char
        return encrypted_text

    def Decrypt(self, text, shift):
        self.text = text
        self.shift = shift
        decrypted_text = ""
        for char in text:
            if char in self.AllSybols:
                old_index = self.AllSybols.find(char)
                new_index = (old_index - self.shift) % len(self.AllSybols)
                decrypted_text += self.AllSybols[new_index]
            else:
                decrypted_text += char
        return decrypted_text