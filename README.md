TO RUN THE STREAMLIT APP:
1) CONNECT MYSQL SERVER
2) MAKE SURE YOUR FIREWALL LETS YOUR HOST IP HAS SPECIAL ACCESS
3) TYPE "streamlit run check.py --server.port 8501 --server.enableCORS true --server.enableXsrfProtection false --server.address 0.0.0.0" in the terminal of your IDE and press enter
4) open another terminal for the dental interface and type "streamlit run dental_camp.py --server.port 8502 --server.enableCORS true --server.enableXsrfProtection false --server.address 0.0.0.0" in the terminal of your IDE and press enter
5) ONCE You're connected, other clients can connect to by typing "http://[Your Host IP]:8501" in their browser
6) FOR MYSQL CONNECTION:
MySQL often restricts connections to localhost.
You need to configure the MySQL user that your Streamlit app uses to allow remote connections.
Change the bind-address in your MySQL configuration file to $0.0.0.0$ (or comment it out) to allow listening on all interfaces.Grant the necessary privileges to the user from the client machines' IP addresses.
For example:SQLCREATE USER 'app_user'@'%' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON your_database.* TO 'app_user'@'%';
FLUSH PRIVILEGES;
The '%' means the user can connect from any host.
7) FOR FIREWALL ACCESS:
Step A: Open Windows Defender Firewall
On the host laptop, press the Windows Key + R to open the Run dialog.
Type wf.msc and press Enter. This opens the Windows Defender Firewall with Advanced Security console.
Step B: Create a New Inbound Rule
In the left pane, click Inbound Rules.
In the right pane (Actions), click New Rule...
Step C: Configure the Rule
Rule Type: Select Port, then click Next.
Protocol and Ports:
Select TCP.
Select Specific local ports.
Enter the port number: 8501.
Click Next.
Action: Select Allow the connection, then click Next.
Profile: Ensure Domain, Private, and Public are all checked (or at least Private and Domain if you are on a restricted network) to cover all connection types. Click Next.

Name: Give the rule a descriptive name, like Streamlit App 8501.

Click Finish.
