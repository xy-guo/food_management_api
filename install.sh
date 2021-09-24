sudo pip3 install -r requirements.txt

sudo  cp ./supervisord.ini   /etc/supervisor/conf.d/food_management_api.ini
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart food_management_api

# mongorestore ./bak/dump/
mkdir uploads
