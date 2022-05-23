#! /bin/bash

# open firefox window
open -a /Applications/Google\ Chrome.app http://www.google.com\

# activate env
source $HOME/.virtualenvs/safewayClipper/bin/postactivate
source $HOME/.virtualenvs/safewayClipper/bin/activate

# wait 2 seconds
sleep 2

# navigate to directory
cd $HOME/Developer/safewayClipper

# run script
python clipper.py -driver chrome

# deactivate
source $HOME/.virtualenvs/safewayClipper/bin/predeactivate
deactivate

# return home
cd ~
