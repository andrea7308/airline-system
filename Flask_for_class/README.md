# Airline Reservation System

A Flask web application for managing airline reservations, flight search, customer bookings, and airline staff operations. This project simulates a database-backed airline system and includes both customer-facing and employee-facing workflows.

## Features

- Customer registration and login
- Public and authenticated flight search
- Ticket purchasing and confirmation
- Review submission for completed flights
- Airline staff registration and login
- Flight creation and airplane management
- Flight status toggling between on-time and delayed
- Customer and flight review views for staff
- Monthly ticket sales reporting with Plotly charts

## Tech Stack

- Python 3
- Flask 
- PyMySQL
- MySQL / Aiven-hosted database
- Pandas
- Plotly
- python-dotenv
- HTML templates with Jinja2
- pytest for smoke testing

## Project Structure

- `init1.py` – main Flask application and route logic
- `AirlineSystem.sql` – database schema and sample data
- `templates/` – frontend pages for customer and airline staff flows
- `certs/` – TLS certificate files needed for database access
- `.env` – environment variables for DB configuration
- `requirements.txt` – project dependencies
- `tests/test.py` – basic project smoke tests

## Prerequisites

Before running the app, ensure you have:

- Python 3.10 or newer
- A MySQL-compatible database instance
- A valid `.env` file with database credentials
- The CA certificate referenced by `AIVEN_CA_PATH`

## Setup

1. Navigate to the project directory.
2. Create and activate a virtual environment:

```bash
python3 -m venv myvenv
source myvenv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Make sure your `.env` file contains values similar to:

```env
AIVEN_HOST=your_host
AIVEN_PORT=your_port
AIVEN_USER=your_user
AIVEN_PASSWORD=your_password
AIVEN_DB=your_database
AIVEN_CA_PATH=certs/ca.pem
```

5. Import the schema into your database using `AirlineSystem.sql`.

## Running the Application

Start the Flask server from the project root:

```bash
python init1.py
```

Then open the app in a browser:

```text
http://127.0.0.1:5000
```

## Main Application Routes

### Customer Endpoints

- `/` – landing page
- `/login` – customer login
- `/register` – customer registration
- `/customerPage` – customer dashboard
- `/searchFlightsCustomer` – search available flights
- `/purchaseFlight/<flight_num>` – purchase page for a specific flight
- `/confirmPurchase` – process ticket purchase
- `/purchaseSuccess` – successful purchase confirmation
- `/reviewPage` – review submissions and past flight history

### Airline Staff Endpoints

- `/airline_staff_login` – airline staff login
- `/airline_staff_registration` – staff registration
- `/airline_staff` – staff dashboard
- `/searchFlights` – staff flight search and filtering
- `/createFlight` – create a new flight
- `/addAirplane` – add an airplane to the airline
- `/toggle_status` – update flight operational status
- `/view_reports` – monthly ticket sales report
- `/view_ratings` – view reviews for a flight
- `/view_customers` – list customers who purchased a specific flight
- `/logout_admin` – logout staff user

## Database Model

The application relies on a relational schema containing entities such as:

- Customer
- Airline
- Airline Staff
- Airplane
- Flight
- Ticket
- Review
- Phone Numbers

## Testing

The repository contains a basic smoke test:

```bash
pytest
```

## Notes

- Passwords are hashed using MD5 before being stored.
- The app runs in debug mode locally for development convenience.
- In a production environment, the Flask secret key and database credentials should be managed more securely.

## License

This project is intended for academic use in the course environment.
