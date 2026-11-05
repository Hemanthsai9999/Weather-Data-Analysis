import mysql.connector
def connect():
 mydb = mysql.connector.connect(
    host ="localhost",
    user = "root",
    password="aimlb3",
    database = "weather_db"
)
 return mydb