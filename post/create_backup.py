import shutil
import os

# Source path
src = input("Enter the source path: ")

# Destination path
dst = input("Enter the destination path: ")

if os.path.isfile(src):
    shutil.copy2(src, dst)
else:
    print("File not found")

