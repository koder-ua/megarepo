VERSION=0.1
NAME=libvirtex
TARGET=dist/$(NAME)-$(VERSION).tar.gz
$(TARGET) : setup.py $(NAME)/* README.txt
		python setup.py sdist
