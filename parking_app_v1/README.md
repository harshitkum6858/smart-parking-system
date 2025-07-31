# Vehicle Parking App (MAD-1 Project)

This is a multi-user web application for managing vehicle parking lots. It has been built using Flask, SQLAlchemy, and Bootstrap.

## Features

- **Dual Roles:** Admin and regular User.
- **Admin Dashboard:** Manage lots, view users, and see revenue charts.
- **User Dashboard:** View available lots, book spots, and view booking history with charts.
- **RESTful API:** Endpoints to fetch data about parking lots.

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd parking_app_v1
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the application:**
    ```bash
    python app.py
    ```

5.  Open your web browser and navigate to `http://127.0.0.1:5000`.

## How to Use

-   **Admin Login:**
    -   Username: `admin`
    -   Password: `admin`
-   **User:**
    -   Register a new account from the registration page and then log in.