# Item catalog project 2 - WSIG and postgreSQL


## Running on a live web server


This is a sample project for Udacity's "Programming Foundations" course, and the Full Stack Web Dev nano-degree.

It can be found at:

* 	http://dev.beaukinstler.com
* 	http://52.5.160.211

In this project, we've built upon the earlier project for a catalog app.  
The initial project's intent was not to have an entirely production ready application, but to demonstrate some of the core concepts 
of authentication, access control, and CRUD operations on a database.

This enhancement has changed the application to use PostgreSQL, running on a web server on the internet, secured in order
to reduce the risk of compromise from brute force SSH access. 

The linux machine tested on was started with a base Ubuntu 16.04.  From there we installed:
- PostgreSQL
- pip
- git
- python 2.7
- a number of python libraries ( see the Pipfile)
- apache2
	- also install `libapache2-mod-wsgi`

I also needed to create a database with a specific name: catalog.  
I created a PostgreSQL user to access the database, also named 'catalog'.

Once setup, the requirements for hardening the server included:
- limit ssh to only use public key, no passwords
- don't allow root remote login
- setup a user for 'grader' for the Udacity grader, and allow login with a private key, and grant sudo rights
- ssh port is change from the default of 22
- the UFW is configured to only allow ntp, ssh (custom port) and http traffic

Finally, I had to alter this app to get it working with PostgreSQL, and running on the server.
In my case, I had to update my google API credentials to allow for the OAuth to originate from my new server.
Since google doesn't allow IPs to be listed, I did have to add a domain name.  I am using dev.beaukinstler.com. 
As long as that URL is used, the Google OAuth will be available.  

### Notes to self
I where I struggled, was getting clear on how Apache and WSGI needed to play with Python scripts, and how the 
permissions need to be set on the directories.  

I used the examples provided by both the home pages of the Apache and Python home pages.

I also needed to revisit how PostgreSQL handles use rights, and authentication via localhost IPv4, and the 
rights needed for the user to create tables (at least initially), and connect and query a database call.
While this was a little tedious, the documentation provided by PostgreSQL's home page, and it's built in 
\help and \? switches got me through it.

One notable thing I found, was that converting my code to PostgreSQL required changing the column sizes.  I haven't dug too
deep, but it seems like SQLight just didn't care that my text columns for storing password hashes was too short.
When the tables were created in PostgreSQL, however, I was getting errors that pointed me in that direction.

Of course, I'm sure I ended up up on stackoverflow, and similar sites while seeing various errors as I tweaked settings,
but I don't know that I have all of them. I'll list in the _Resources Used_ what I do know I used.

### Resources used
[Original Project](https://github.com/beaukinstler/fswd-item-catalog)
	- Credit to all the resources used to create this original project, including instruction and the code reviews from Udacity

https://stackoverflow.com/questions/13485030/strange-postgresql-value-too-long-for-type-character-varying500

https://httpd.apache.org/docs/2.2/

https://unix.stackexchange.com/questions/76710/changing-timezone-on-debian-keeps-local-time-in-utc

[Troubleshooting SQLAlchemy](http://docs.sqlalchemy.org/en/latest/faq/sessions.html#this-session-s-transaction-has-been-rolled-back-due-to-a-previous-exception-during-flush-or-similar)

https://www.digitalocean.com/community/tutorials/how-to-set-up-apache-virtual-hosts-on-ubuntu-14-04-lts


http://flask-httpauth.readthedocs.io/en/latest/

https://modwsgi.readthedocs.io/en/develop/user-guides/quick-configuration-guide.html

http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls

https://www.postgresql.org/docs/9.0/static/sql-grant.html

https://stackoverflow.com/a/36162748/811479

http://flask.pocoo.org/docs/0.12/deploying/mod_wsgi/

https://www.digitalocean.com/community/tutorials/how-to-secure-postgresql-against-automated-attacks






### Summary of configurations.

1. Apache2 site
	- Primary change was the adding a config to `sites-available`.
		1. First disabled the default site
		2. then crated a conf file in site-available for my site
			* Key elements for WSGI
				1. Choose the user and group for the daemon process.
				2. The alias. So if going to the root or the URL, or /some_sub_dir,
					the site knows where to find the app code.
				3. Finally, in the `Directory` section, `WSGIScriptReloading On` was 
					set so I my changes would auto load, instead of having to reload.	
		3. then enabled that site.
	- Here's view of the conf

			<VirtualHost *:80>
					ServerName dev.beaukinstler.com
					
					DocumentRoot /var/www/fswd

					Alias /robots.txt /var/www/fswd/robots.txt     
					
					<Directory /var/www/fswd>
							Order allow,deny
							Allow from all
					</Directory>

					WSGIDaemonProcess mycatalogapp user=catalog group=catalog threads=5
					WSGIScriptAlias / /var/www/scripts/catalog/myapp.wsgi

					<Directory /var/www/scripts/catalog>
							WSGIProcessGroup mycatalogapp
							WSGIApplicationGroup %{GLOBAL}
							Order deny,allow
							Allow from all
							WSGIScriptReloading On
					</Directory>
			</VirtualHost>


2. Database 
	- After installing the server, I created the `catalog` database, and `catalog` user.
	- Initially, since the connection string uses the `catalog` user to authenticate,
		I needed to allow the user to have access to create tables. So I started out granting ALL PRIVILEGES to the catalog user. 
	- Using `sudo su postgres` to get access, i used this command
		 	
			psql -d catalog -c "GRANT ALL PRIVILEGES ON DATABASE catalog TO catalog;"
	- To change the app from using SQLite to PostgreSQL, I needed to change the SQLAlchemy
		engine setup. I load my connection string from a json file, but essentially its this:

			postgresql+psycopg2://catalog:<password>@localhost/<database_name>
	- Finally, upon first attempt to use Google Auth, I found my database column in the user
		table that hold the password hash was too small, and I had to change the size of the column.  I used this command.

			psql -d catalog -c "ALTER TABLE user ALTER COLUMN password_hash varchar(255)" 

3. SSH/User setup
	- In `/etc/ssh/sshd.conf`
		- disable password remote login
		- disable root key based remote login
		- change the listening port

4. Firewall
	- ufw allow
		- 123/udp
		- 80/tcp
		- 22/tcp (not actually 22)

---

		ubuntu@dev:~$ sudo ufw status numbered
		Status: active
		To                         Action      From
		--                         ------      ----
		[ 1] sshx/tcp                   ALLOW IN    Anywhere                  
		[ 2] 80/tcp                     ALLOW IN    Anywhere                  
		[ 3] 123/udp                    ALLOW IN    Anywhere                  
		[ 4] sshx/tcp (v6)              ALLOW IN    Anywhere (v6)             
		[ 5] 80/tcp (v6)                ALLOW IN    Anywhere (v6)             
		[ 6] 123/udp (v6)               ALLOW IN    Anywhere (v6)

5. Finally, changed file rights, to that the `catalog` user can't access .git dir in the
	directory.
