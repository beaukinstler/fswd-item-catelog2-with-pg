# Item catalog project


## Running on a live web server


This is a sample project for Udacity's "Programming Foundations" course, and the Full Stack Web Dev nano-degree.

In this project, we've built upon the earlier project for a catalog app.  
The intial project's intent was not to have an entirely production ready application, but to demonstrate some of the core concepts 
of authentication, access control, and CRUD operations on a database.

This enhancment has change the application to use PostgreSQL, running on a web server on the internet, secured in order
to reduce the risk of compromise from brute force SSH access. 

The linux machine tested on was started with a base Ubuntu 16.04.  From there we installed:
- PostreSQL
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
- the UFW is configured to only allow ntp, ssh (custom port) and http trafic

Finally, I had to alter this app to get it working with PostgresSQL, and running on the server.
In my case, I had to update my google API credentials to allow for the OAuth to originate from my new server.
Since google doesn't allow IPs to be listed, I did have to add a domain name.  I am using dev.beaukinstler.com. 
As long as that URL is used, the Google OAuth will be available.  

### Notes to self
I where I struggled, was getting clear on how Apache and WSGI needed to play with Python scripts, and how the 
permissions need to be set on the directories.  

I used the examples provided by both the home pages of the Apache and Python home pages.

I also needed to revisit how PostgreSQL handles use rights, and authentication via localhost IPv4, and the 
rights needed for the user to create tables (at least initially), and connect and query a database call.
While this was a little tedius, the documentation provided by PostgreSQL's home page, and it's built in 
\help and \? switches got me through it.

One noteable thing I found, was that converting my code to PostgreSQL required changing the column sizes.  I haven't dug too
deep, but it seems like SQLight just didn't care that my text colmns for storing password hashes was too short.
When the tables were created in PostgreSQL, however, I was getting errors that pointed me in that direction.

Of course, I'm sure I ended up up on stackoverflow, and simlilar sites while seeing various errors as I tweeked settings,
but I don't know that I have all of them. I'll list in the _REFERENCES_ what I do know I used.

### Resources used
[Original Project](https://github.com/beaukinstler/fswd-item-catalog)
- Credit to all the resoures used to create this original project, including intruction and the code reviews from Udacity
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
	- Primary change was the sites.
		1. first disabled the default site
		2. then crated a conf file in site-available for my site
		3. then enabled that site.
	- Here's view of the conf  

2. Database 
	- 

3. SSH/User setup
	- in `/etc/ssh/sshd.conf`
		- diable password remote login
		- disable root key based remote login
		- change the listening port

4. Firewall
	- ufw allow
		- 123/udp
		- 80/tcp
		- 22/tcp (not actaully 22)

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


