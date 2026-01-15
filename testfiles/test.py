# import requests

# url = "http://127.0.0.1:8000/media"

# # Open the image in Binary Mode ('rb')
# with open("codephoto.png", "rb") as f:
#     # The key 'file' must match the parameter name in your FastAPI function
#     files = {"file": ("my_code.png", f, "image/jpeg")}
#     response = requests.post(url, files=files)
# print(files)
    
# print(response.json())