coverage run -m manage test --testrunner="testrunner.Runner" $1 
cat testresults.txt 
coverage html
coverage json