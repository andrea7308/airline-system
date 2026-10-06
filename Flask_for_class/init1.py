#Import Flask Library

from flask import Flask, g, render_template, request, session, url_for, redirect
import pymysql.cursors
import os
from dotenv import load_dotenv
from datetime import datetime # necessary for obtaining the current date and time
import hashlib # this is used in the md5 helper func
import random # this is used for the flight_num generation for inserting values into Flight
import pandas as pd
import plotly.express as px


from functools import wraps # this is to use the protected thingy we learned from class
import json
import random

# load_dotenv('/Users/sabriaislam/DB_AirlineSystem/Flask_for_class/.env')
load_dotenv()

#Initialize the app from Flask
app = Flask(__name__)

# Ideally load these from environment variables
AIVEN_HOST = os.getenv("AIVEN_HOST")
AIVEN_PORT = int(os.getenv("AIVEN_PORT", "22766"))
AIVEN_USER = os.getenv("AIVEN_USER")
AIVEN_PASSWORD = os.getenv("AIVEN_PASSWORD")
AIVEN_DB = os.getenv("AIVEN_DB")
AIVEN_CA_PATH = os.getenv("AIVEN_CA_PATH")

def get_db_connection():
	if 'db_connection' not in g:
		g.db_connection = pymysql.connect(
			host=AIVEN_HOST,
			port=AIVEN_PORT,
			user=AIVEN_USER,
			password=AIVEN_PASSWORD,
			database=AIVEN_DB,
			charset='utf8mb4',
			cursorclass=pymysql.cursors.DictCursor,
			ssl={"ca": AIVEN_CA_PATH}
		)
	return g.db_connection


@app.teardown_appcontext
def close_db_connection(exception=None):
	connection = g.pop('db_connection', None)
	if connection is not None:
		connection.close()


#Define a route to hello function
@app.route('/')
def hello():
	return render_template('index.html')


# ====== CUSTOMER LOGIN AND REGISTRATION PAGE RENDERING ======
#Define route for login
@app.route('/login')
def login():
	return render_template('customer_login.html')

#Define route for register
@app.route('/register')
def register():
	return render_template('customer_register.html')


# ====== AIRLINE STAFF LOGIN AND REGISTRATION PAGE RENDERING ======
# Defines route for airline staff registration page
@app.route('/airline_staff_registration')
def airlineReg():
	return render_template('airline_staff_registration.html')


# Defines route for the airline staff login page
@app.route('/airline_staff_login')
def airlineLog():
	return render_template('airline_staff_login.html')

# This is a decorator that will make the route only accessible to logged in airline staff
# Make sure to import functools
def protected_route(route):
	@wraps(route)
	def wrapper(*args, **kwargs):
		if session.get('username'):
			return route(*args, **kwargs) # Direct to the actual function implementation
		else:
			return render_template('index.html') # Redirect to unauthorized page or whatever of your choice
	return wrapper


# ========== AIRLINE STAFF RELATED FUNCTIONS ==========

# authenticates the register - admin register
@app.route('/airlineRegAuth', methods=['GET', 'POST'])
def airlineRegAuth():
	#grabs information from the forms
	# username has to be checked if already exists
	admin_username = request.form['username']

	# airline_name has to be checked if exists
	airline_name = request.form['airline_name']

	# rest of the attributes needed for registration
	password = request.form['password']
	first_name = request.form['first_name']
	last_name = request.form['last_name']
	dob = request.form['dob']
	airlinestaff_email = request.form['airlinestaff_email']

	#cursor used to send queries; general purpose connection with the db
	cursor = get_db_connection().cursor()

	# check if the username is already taken in Airline_Staff table
	query = 'SELECT * FROM Airline_Staff WHERE username = %s;'
	cursor.execute(query, (admin_username))
	#stores the results in a variable
	data = cursor.fetchone()

	# check if the airline name is present in the Airline table
	query = 'SELECT * FROM Airline WHERE airline_name = %s;'
	cursor.execute(query, (airline_name))
	
	data2 = cursor.fetchone()

	if(data):
		#If the previous query returns data, then user exists
		error = "This user already exists"
		return render_template('airline_staff_registration.html', error = error)
	elif(not data2):
		# this means the airline isn't present in the Airline table; return error
		error = "Enter a valid airline"
		return render_template('airline_staff_registration.html', error = error)
	else:
		# insert the appropriate values into the Airline_Staff table
		# insertions are in the order which tuple for the Airline_Staff table must be inserted
		ins = 'INSERT INTO Airline_Staff VALUES(%s, %s, %s, %s, %s, %s, %s);'
		# password must be hashed before being inserted into the table; done through helper func
		cursor.execute(ins, (admin_username, hashPass(password), first_name, last_name, dob, airlinestaff_email, airline_name))
		get_db_connection().commit()

		# get all values for the same name attributes
		phone_numbers = list(set(request.form.getlist('phone_number')))
		query = 'insert into Phone_Numbers values(%s, %s);'
		for i in range(len(phone_numbers)):
			if (not (phone_numbers[i] == '')):
				# admin_username is still accessible here
				phone_number = phone_numbers[i]
				cursor.execute(query, (admin_username, phone_number))

		# close the cursor's connection and commit changes
		get_db_connection().commit()
		cursor.close()

		# send the user to the airline staff login page
		return render_template('airline_staff_login.html')


#Authenticates the login for airline staff
@app.route('/airlineLogAuth', methods=['GET', 'POST'])
def airlineLogAuth():
	#grabs information from the forms
	username = request.form['username']
	password = hashPass(request.form['password'])

	#cursor used to send queries
	cursor = get_db_connection().cursor()
	#executes query
	query = 'SELECT * FROM Airline_Staff WHERE username = %s and password = %s;'
	cursor.execute(query, (username, password))
	#stores the results in a variable
	data = cursor.fetchone()
	cursor.close()
	if(data):
		#creates a session for the the user
		#session is a built in
		session['username'] = username
		session['airline_name'] = data['airline_name']
		return redirect(url_for('airline_staff'))
	else:
		#returns an error message to the html page
		error = 'Invalid login or username'
		return render_template('airline_staff_login.html', error=error)


@app.route('/airline_staff')
@protected_route
def airline_staff():
	username = session['username']
	airline_name = session['airline_name']
	cursor = get_db_connection().cursor()
	# default for search flights:
	curr_date = getDateTime() # helper func which gets the curr date, and puts it in the right format to query for it in the db
	query = 'select * from Flight where departure_date_time between %s and DATE_ADD(%s, INTERVAL 30 DAY) and airline_name = %s;'
	cursor.execute(query, (curr_date, curr_date, airline_name))

	flights = cursor.fetchall()

	# for the create flights feature, get the airplane ids for the drop down and the initial airplane table
	query = 'select * from Airplane where airline_name = %s;'
	cursor.execute(query, (airline_name))
	airplanes = cursor.fetchall()

	# add airplanes to session so that it persists until the airline_staff logs out
	session['airplanes'] = airplanes

	cursor.close()
	return render_template('airline_staff.html', flights=flights, airplanes=airplanes)

# Search for flights as an airline staff
@app.route('/searchFlights', methods=['GET', 'POST'])
@protected_route
def searchFlights():
	start_date = request.form['start_date']
	end_date = request.form['end_date']
	dept_code = request.form['dept_code']
	arr_code = request.form['arr_code']
	airline_name = session['airline_name']

	# cursor used to send queries; used to interface with the database!
	cursor = get_db_connection().cursor()

	# to shorten the cases, you can either have:
	# none (default); no input given to the search
	if (not start_date and not end_date and not dept_code and not arr_code):
		curr_date = getDateTime()
		query = 'select * from Flight where departure_date_time between %s and DATE_ADD(%s, INTERVAL 30 DAY) and airline_name = %s;'
		cursor.execute(query, (curr_date, curr_date, airline_name))

		flights = cursor.fetchall()
		cursor.close()
		return render_template('airline_staff.html', flights=flights, airplanes=session['airplanes'])
	# all
	elif (start_date and end_date and dept_code and arr_code):
		# use helper function to convert the times from form to appropriate type
		start_date = datetimelocalToDatetime(start_date)
		end_date = datetimelocalToDatetime(end_date)
		query = 'select * from Flight where departure_date_time between %s and %s and dept_airport = %s and arr_airport = %s and airline_name = %s;'
		cursor.execute(query, (start_date, end_date, dept_code, arr_code, airline_name))

		flights = cursor.fetchall()
		cursor.close()
		return render_template('airline_staff.html', flights=flights, airplanes=session['airplanes'])
	# only start and end dates
	elif (start_date and end_date and not dept_code and not arr_code):
		# use helper function to convert the times from form to appropriate type
		start_date = datetimelocalToDatetime(start_date)
		end_date = datetimelocalToDatetime(end_date)
		query = 'select * from Flight where departure_date_time between %s and %s and airline_name = %s;'
		cursor.execute(query, (start_date, end_date, airline_name))

		flights = cursor.fetchall()
		cursor.close()
		return render_template('airline_staff.html', flights=flights, airplanes=session['airplanes'])
	# only dept and arr airport codes
	elif (not start_date and not end_date and dept_code and arr_code):
		query = 'select * from Flight where dept_airport = %s and arr_airport = %s and airline_name = %s;'
		cursor.execute(query, (dept_code, arr_code, airline_name))

		flights = cursor.fetchall()
		cursor.close()
		return render_template('airline_staff.html', flights=flights, airplanes=session['airplanes'])
	else:
		error = 'You must choose a date range, departure and arrival airports, or both'
		cursor.close()
		return render_template('airline_staff.html', error=error, airplanes=session['airplanes'])


# Create flights as an airline staff
@app.route('/createFlight', methods=['GET', 'POST'])
@protected_route
def createFlight():
	# values which will be inserted into the db; are in basic order in which they will be inserted
	airplane_id = request.form.get('airplane_name')
	airline_name = session['airline_name']
	flight_num = randomNumberSize20() # flight num has to be unique within a given airline; accomplished through random number generation with max size of varchar(20)
	departure_date_time = request.form['departure_date_time']
	arrival_date_time = request.form['arrival_date_time']
	dept_airport = request.form['dept_airport']
	arr_airport = request.form['arr_airport']
	flight_price = request.form['flight_price']
	flight_status = 'on-time' # this will be the default status for a flight; can later be changed once inserted

	# checks if drop down menu value was selected or not
	if (not airplane_id):
		error2 = 'Please select an airplane from the dropdown menu'
		return render_template('airline_staff.html', error2 = error2, airplanes=session['airplanes'])

	cursor = get_db_connection().cursor()

	query = 'insert into Flight values (%s, %s, %s, %s, %s, %s, %s, %s, %s)'
	cursor.execute(query, (airplane_id, airline_name, flight_num, departure_date_time, arrival_date_time, dept_airport, arr_airport, flight_price, flight_status))

	get_db_connection().commit()
	cursor.close()

	return redirect(url_for('airline_staff')) # used redirect so that the page reloads with all the updated elements


# Add an airplane to the airline you work for
@app.route('/addAirplane', methods=['GET', 'POST'])
@protected_route
def addAirplane():
	airline_name = session['airline_name']
	num_of_seats = request.form['num_of_seats']
	manufacture_comp = request.form['manufacture_comp']
	age = request.form['age']
	airplane_id = request.form['airplane_id']

	cursor = get_db_connection().cursor()
	# check if not already in database
	query = 'select * from Airplane where airline_name = %s and airplane_id = %s;'
	cursor.execute(query, (airline_name, airplane_id))

	data = cursor.fetchone()
	if(data):
		error = 'Airplane with the same id already exists'
		cursor.close()
		return render_template('airline_staff.html', error3=error)
	else:
		# insert into Airplane
		query = 'insert into Airplane values (%s, %s, %s, %s, %s)'
		cursor.execute(query, (num_of_seats, manufacture_comp, age, airplane_id, airline_name))

		# commit changes
		get_db_connection().commit()
		

		# update the value of session['airplanes'], since it now has a new airplane in it:
		query = 'select * from Airplane where airline_name = %s;'
		cursor.execute(query, (airline_name))
		session['airplanes'] = cursor.fetchall()

		cursor.close()
		# reload the page so that new data may be added
		return redirect(url_for('airline_staff'))


# Toggle the status of a flight which the toggle button was pressed for; toggle button on search flights table
@app.route("/toggle_status", methods=['GET', 'POST'])
@protected_route
def toggle_status():
	airline_name = session['airline_name']
	flight_num = request.form['flight_num']
	departure_date_time = request.form['departure_date_time']

	cursor = get_db_connection().cursor()

	# fetch current status
	query = 'select * from Flight where flight_num = %s and departure_date_time = %s and airline_name = %s;'
	cursor.execute(query, (flight_num, departure_date_time, airline_name))
	# result will be one row, since we used primary key as query arguments
	data = cursor.fetchone()

	# get the current status which the flight is
	current_status = (data)['flight_status'].lower() # did this b/c we inserted on-time and delayed in uppercase sometimes in our test cases

	# depending on what the status is currently, change it to something new
	new_status = "on-time" if current_status == "delayed" else "delayed"

	# update the flight status to the new status value
	query = 'update Flight set flight_status = %s where flight_num = %s and departure_date_time = %s and airline_name = %s;'
	cursor.execute(query, (new_status, flight_num, departure_date_time, airline_name))

	get_db_connection().commit()
	cursor.close()

	# load the whole page again; this time will reflect our changes
	return redirect(url_for('airline_staff'))

## Create bar chart of monthly ticket spendings ###
@app.route("/view_reports", methods=["GET","POST"])
@protected_route
def view_reports():
	start_date = request.args.get('start_date')
	end_date = request.args.get('end_date')
	query = """SELECT DATE_FORMAT(purchase_date_time, '%%Y-%%m') AS month, COUNT(*) AS tickets_sold
		FROM Ticket
		WHERE purchase_date_time BETWEEN %s AND %s
		GROUP BY month
		ORDER BY month;
	"""

	cursor = get_db_connection().cursor()
	cursor.execute(query, (start_date, end_date))
	data = cursor.fetchall()
	df = pd.DataFrame(data)

	if df.empty:
		error = "No data available for the selected range."
		cursor.close()
		return render_template("airline_staff.html", error4=error)

	fig = px.bar(
        df,
        x="month",
        y="tickets_sold",
        title=f"Tickets Sold per Month ({start_date} to {end_date})",
        labels={"month": "Month", "tickets_sold": "Tickets Sold"}
    )
	graph_html = fig.to_html(full_html=False)
	
	cursor.close()

	return render_template(
        "airline_staff.html",
        graph_html=graph_html,
        start_date=start_date,
        end_date=end_date
    )

# 'View flight ratings' functionality
@app.route('/view_ratings', methods=['GET', 'POST'])
@protected_route
def view_ratings():
	airline_name = session['airline_name']
	flight_num = request.form['flight_num']
	departure_date_time = request.form['departure_date_time']

	cursor = get_db_connection().cursor()
	# for both, remember to deal with the case that no info is returned
	# get all the ratings related to the flight
	query = 'select rate, comment from Review where airline_name = %s and flight_num = %s and departure_date_time = %s;'
	cursor.execute(query, (airline_name, flight_num, departure_date_time))
	
	reviews = cursor.fetchall()

	# get the avg ratings
	query = 'select sum(rate) / count(rate) as average_rating from Review where airline_name = %s and flight_num = %s and departure_date_time = %s;'
	cursor.execute(query, (airline_name, flight_num, departure_date_time))

	average_rating = (cursor.fetchone())['average_rating']
	
	cursor.close()
	return render_template('airline_staff.html', reviews = reviews, average_rating = average_rating, airplanes=session['airplanes'])


# Write a function that displays all the customers which have purchased a flight. This
# can be added as another button to the search menu for each flight, which shouldn't be hard.
# 'View customers' functionality
@app.route('/view_customers', methods=['GET', 'POST'])
@protected_route
def view_customers():
	airline_name = session['airline_name']
	flight_num = request.form['flight_num']
	departure_date_time = request.form['departure_date_time']

	cursor = get_db_connection().cursor()
	query = '''
	select c.customer_email, c.first_name, c.last_name, c.phone_number, c.passport_num,
	c.passport_expiration, c.passport_country, c.dob
	from Customer as c natural join (Flight natural join Ticket)
	where airline_name = %s and flight_num = %s and departure_date_time = %s;
	'''
	cursor.execute(query, (airline_name, flight_num, departure_date_time))
	customers = cursor.fetchall()
	
	cursor.close()
	return render_template('airline_staff.html', customers=customers, airplanes=session['airplanes'])


@app.route('/logout_admin')
def logout_admin():
	session.pop('username')
	session.pop('airline_name')
	session.pop('airplanes')
	return redirect('/')

# ========== CUSTOMER RELATED FUNCTIONS ==========

#Authenticates the register
@app.route('/registerAuthCustomer', methods=['GET', 'POST'])
def registerAuthCustomer():

	#stores the necessary info from customer
	customer_email = request.form['customer_email']
	first_name = request.form["first_name"]
	last_name = request.form["last_name"]
	password = request.form["password"]
	building_num = request.form["building_num"]
	street = request.form["street"]
	city = request.form["city"]
	state = request.form["state"]
	phone_number = request.form["phone_number"]
	passport_num = request.form["passport_num"]
	passport_expiration = request.form["passport_expiration"]
	passport_country = request.form["passport_country"]
	dob = request.form["dob"]

	#cursor used to send queries
	cursor = get_db_connection().cursor()
	#executes query
	query = 'SELECT * FROM Customer WHERE customer_email = %s'
	cursor.execute(query, (customer_email))
	#stores the results in a variable
	data = cursor.fetchone()
	error = None
	if(data):
		#If the previous query returns data, then user exists
		error = "This user already exists"
		cursor.close()
		return render_template('customer_register.html', error = error)
	else:
		ins = 'INSERT INTO Customer VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'
		cursor.execute(ins, (
				customer_email, first_name, last_name, 
				hashPass(password), building_num, street, 
				city, state, phone_number, passport_num, 
				passport_expiration, passport_country, dob
				)
		)
		get_db_connection().commit()
		cursor.close()
		return render_template('index.html')

#Authenticates the customer login
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
	#grabs information from the forms
	username = request.form['username']
	password = hashPass(request.form['password'])

	#cursor used to send queries
	cursor = get_db_connection().cursor()
	#executes query
	query = 'SELECT * FROM Customer WHERE customer_email = %s and password = %s'
	cursor.execute(query, (username, password))
	#stores the results in a variable
	data = cursor.fetchone()
	#use fetchall() if you are expecting more than 1 data row (just notes for my own learning)
	cursor.close()
	if(data):
		#creates a session for the the user
		#session is a built in
		session['username'] = username
		cursor.close()
		return redirect(url_for('customerPage'))
	else:
		#returns an error message to the html page
		error = 'Invalid login or username'
		cursor.close()
		return render_template('customer_login.html', error=error)
	
# Main Customer page that shows the upcoming flights of customer and buttons for other actions
@app.route('/customerPage', methods=['GET', 'POST'])
@protected_route
def customerPage():
	customer_email = session.get('username')
	cursor = get_db_connection().cursor()
	
	query1 ="""
			select t.ticket_id, t.airline_name, t.flight_num, 
				f.departure_date_time, f.arrival_date_time 
			from Ticket as t 
			join Flight as f 
			on t.airline_name = f.airline_name 
			and t.flight_num = f.flight_num 
			and t.departure_date_time = f.departure_date_time 
			where t.customer_email = %s 
			and f.departure_date_time >= now()
			"""
	cursor.execute(query1, (customer_email,))
	data1 = cursor.fetchall()

	cursor.close()
	return render_template('customer.html', customer_email=customer_email, flights=data1)

@app.route('/reviewPage', methods=['GET'])
@protected_route
def reviewPage():
	customer_email = session.get('username')
	cursor = get_db_connection().cursor()

	error = request.args.get('error')

	# all the reviews made by customer
	query1 ="""
			select rate, comment, airline_name, departure_date_time, flight_num
			from Review 
			where customer_email = %s
			"""
	
	cursor.execute(query1, (customer_email,))
	reviews = cursor.fetchall()

	query2 ="""
			select t.ticket_id, t.airline_name, t.flight_num, 
				f.departure_date_time, f.arrival_date_time 
			from Ticket as t 
			join Flight as f 
			on t.airline_name = f.airline_name 
			and t.flight_num = f.flight_num 
			and t.departure_date_time = f.departure_date_time 
			where t.customer_email = %s 
			and f.departure_date_time < now()
			"""
	
	cursor.execute(query2, (customer_email,))
	flights = cursor.fetchall()

	cursor.close()

	return render_template('reviews.html', reviews=reviews, flights=flights, error=error )

@app.route('/review', methods=['POST'])
def review():
	customer_email = session.get('username')
	cursor = get_db_connection().cursor()

	flight_info = json.loads(request.form['flight'])
	airline_name = flight_info['airline_name']
	flight_num = flight_info['flight_num']
	departure_date_time = flight_info['departure_date_time']

	rating = request.form['rating']
	comment = request.form['comment']

	query = """
			select customer_email
			from Review
			where customer_email = %s
			and flight_num = %s
			and departure_date_time = %s
			and airline_name = %s
			"""
	cursor.execute(query, (customer_email, flight_num, departure_date_time, airline_name))
	
	if cursor.fetchone():
		cursor.close()
		return redirect(url_for('reviewPage', error="You've already left a review for this flight"))
	
	ins ="""
		 insert into Review(customer_email, flight_num, 
		 	departure_date_time, airline_name, rate, comment) 
		 values (%s, %s, %s, %s, %s, %s)
		 """

	cursor.execute(ins, (customer_email, flight_num, departure_date_time, airline_name, rating, comment))
	get_db_connection().commit()
	cursor.close()

	return redirect(url_for('reviewPage'))

@app.route('/purchaseFlight/<flight_num>', methods=['GET'])
@protected_route
def purchaseFlight(flight_num):
	cursor = get_db_connection().cursor()

	query = """
			SELECT * FROM Flight
			WHERE flight_num = %s
    		"""
	cursor.execute(query, (flight_num,))
	flight = cursor.fetchone()

	cursor.close()
	return render_template('purchaseFlight.html', flight=flight)

@app.route('/confirmPurchase', methods=['POST'])
def confirmPurchase():
	customer_email = session['username']
	cursor = get_db_connection().cursor()

	airline_name = request.form['airline_name']
	flight_num = request.form['flight_num']
	departure_date_time = request.form['departure_date_time']

	check =	"""
			SELECT * FROM Ticket
			WHERE customer_email = %s
			AND airline_name = %s
			AND flight_num = %s
			AND departure_date_time = %s
    		"""

	cursor.execute(check, (customer_email, airline_name, flight_num, departure_date_time))
	if cursor.fetchone():
			query1 = """
					select t.ticket_id, t.airline_name, t.flight_num, 
						f.departure_date_time, f.arrival_date_time 
					from Ticket as t 
					join Flight as f 
					on t.airline_name = f.airline_name 
					and t.flight_num = f.flight_num 
					and t.departure_date_time = f.departure_date_time 
					where t.customer_email = %s 
							
					"""
			cursor.execute(query1, (customer_email,))
			flights = cursor.fetchall()
			
			cursor.close()

			return render_template('customer.html', customer_email=customer_email, flights=flights,
								message="You already purchased a ticket for this flight.")


	cursor.execute("select ticket_id from Ticket")
	all_ticket_ids = [row['ticket_id'] for row in cursor.fetchall()]

	
	ticket_id = random.randint(1000, 9999)
	while ticket_id in all_ticket_ids:
		ticket_id = random.randint(1000, 9999)

	card_type = request.form['card_type']
	card_number = request.form['card_number']
	name_on_card = request.form['name_on_card']
	card_exp_date = request.form['card_exp_date']
	card_exp_date = card_exp_date + "-01" 

	ins="""
		insert into Ticket ( 
			ticket_id,
			card_type,
			card_number,
			name_on_card,
			purchase_date_time,
			card_exp_date,
			customer_email,
			airline_name,
			flight_num,
			departure_date_time
		)
		values (%s, %s, %s, %s, now(), %s, %s, %s, %s, %s)
		"""
	
	cursor.execute(ins, (
		ticket_id, 
		card_type, 
		card_number, 
		name_on_card, 
		card_exp_date, 
		customer_email, 
		airline_name, 
		flight_num, 
		departure_date_time
	))
	
	get_db_connection().commit()
	cursor.close()

	return redirect(url_for('purchaseSuccess'))

@app.route('/purchaseSuccess')
def purchaseSuccess():
    return render_template('purchaseSuccess.html')


@app.route('/searchFlightsCustomer', methods=['GET', 'POST'])
@protected_route
def searchFlightsCustomer():
	cursor = get_db_connection().cursor()
	trip_type = request.args.get('trip_type', 'oneway')
	dept_airport = request.args.get('dept_airport')
	arr_airport = request.args.get('arr_airport')
	depart_date = request.args.get('depart_date')
	return_date = request.args.get('return_date')

	outbound_flights = []
	return_flights = []
	if dept_airport and arr_airport and depart_date:
		cursor = get_db_connection().cursor(pymysql.cursors.DictCursor)
		outbound_query = """
			SELECT 
				f.airline_name,
				f.flight_num,
				f.departure_date_time,
				f.arrival_date_time,
				f.dept_airport,
				f.arr_airport,
				f.flight_price,
				f.flight_status,
				a.num_of_seats,
				COUNT(t.ticket_id) AS tickets_sold
			FROM Flight AS f
			JOIN Airplane AS a 
				ON f.airplane_id = a.airplane_id 
				AND f.airline_name = a.airline_name
			LEFT JOIN Ticket AS t 
				ON t.airline_name = f.airline_name
			AND t.flight_num = f.flight_num
			AND DATE(t.departure_date_time) = DATE(f.departure_date_time)
			WHERE f.dept_airport = %s
			AND f.arr_airport = %s
			AND DATE(f.departure_date_time) = %s
			GROUP BY 
				f.airline_name,
				f.flight_num,
				f.departure_date_time,
				a.num_of_seats
			HAVING tickets_sold < a.num_of_seats
			"""
		cursor.execute(outbound_query, (dept_airport, arr_airport, depart_date))
		outbound_flights = cursor.fetchall()
	if trip_type == 'roundtrip' and return_date:
		cursor = get_db_connection().cursor(pymysql.cursors.DictCursor)
		return_query = """
			SELECT 
				f.airline_name,
				f.flight_num,
				f.departure_date_time,
				f.arrival_date_time,
				f.dept_airport,
				f.arr_airport,
				f.flight_price,
				f.flight_status,
				a.num_of_seats,
				COUNT(t.ticket_id) AS tickets_sold
			FROM Flight AS f
			JOIN Airplane AS a 
				ON f.airplane_id = a.airplane_id 
				AND f.airline_name = a.airline_name
			LEFT JOIN Ticket AS t 
				ON t.airline_name = f.airline_name
			AND t.flight_num = f.flight_num
			AND DATE(t.departure_date_time) = DATE(f.departure_date_time)
			WHERE f.dept_airport = %s
			AND f.arr_airport = %s
			AND DATE(f.departure_date_time) = %s
			GROUP BY 
				f.airline_name,
				f.flight_num,
				f.departure_date_time,
				a.num_of_seats
			HAVING tickets_sold < a.num_of_seats
			"""
		
		cursor.execute(return_query, (arr_airport, dept_airport, return_date))
		return_flights = cursor.fetchall()
		cursor.close()
	return render_template('searchFlightsCustomer.html', outbound_flights=outbound_flights, return_flights=return_flights,
    trip_type=trip_type)

# customer logout
@app.route('/logout')
def logout():
	session.pop('username')
	return redirect('/')

# public flight search
@app.route('/search_flights', methods=['GET'])
def search_flights():
	trip_type = request.args.get('trip_type', 'oneway')
	dept_airport = request.args.get('dept_airport')
	arr_airport = request.args.get('arr_airport')
	depart_date = request.args.get('depart_date')
	return_date = request.args.get('return_date')

	outbound_flights = []
	return_flights = []
	if dept_airport and arr_airport and depart_date:
		cursor = get_db_connection().cursor(pymysql.cursors.DictCursor)
		outbound_query = """
            SELECT *
            FROM Flight
            WHERE dept_airport = %s
              AND arr_airport = %s
              AND DATE(departure_date_time) = %s
        """
		cursor.execute(outbound_query, (dept_airport, arr_airport, depart_date))
		outbound_flights = cursor.fetchall()
	if trip_type == 'roundtrip' and return_date:
		cursor = get_db_connection().cursor(pymysql.cursors.DictCursor)
		return_query = """
                SELECT *
                FROM Flight
                WHERE dept_airport = %s
                  AND arr_airport = %s
                  AND DATE(departure_date_time) = %s
            """
		cursor.execute(return_query, (arr_airport, dept_airport, return_date))
		return_flights = cursor.fetchall()
		cursor.close()
	return render_template('search_flights.html', outbound_flights=outbound_flights, return_flights=return_flights,
    trip_type=trip_type)


# Helper functions
# Get the current date and time in the appropriate format
def getDateTime():
	now = datetime.now()
	# return the curr date returned from the library func in the appropriate format for querying
	return now.strftime("%Y-%m-%d %H:%M:%S")


# Switch the datetime-local format to the appropriate format
def datetimelocalToDatetime(datetimelocal):
	# datetimelocal is from request.form[]
	# parse the datetime-local format
	dt = datetime.fromisoformat(datetimelocal)

	# format it to "YYYY-MM-DD HH:MM:SS"
	formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
	return formatted


# Create a random number of max length 20
def randomNumberSize20():
    return str(random.randrange(0, 10**20))


# hashes passwords using MD5
def hashPass(password):
	# create a new MD5 hash object
	m = hashlib.md5()

    # update the hash object with the bytes-like object (encoded string)
	m.update(password.encode('utf-8'))

    # get the hash in a human-readable hexadecimal format
	md5_hash = m.hexdigest()

	return md5_hash

		
app.secret_key = 'some key that you will never guess'
#Run the app on localhost port 5000
#debug = True -> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
	app.run('127.0.0.1', 5000, debug = True)
