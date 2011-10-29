VERSION=0.3
NAME=vm_utils
TARGET=dist/$(NAME)-$(VERSION).tar.gz
$(TARGET) : setup.py $(NAME)/* README.txt
		python setup.py sdist
