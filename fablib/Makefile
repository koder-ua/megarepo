VERSION=0.1
NAME=fablib
TARGET=dist/$(NAME)-$(VERSION).tar.gz
$(TARGET) : setup.py $(NAME)/* README.txt
		python setup.py sdist
