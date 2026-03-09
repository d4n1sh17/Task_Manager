# Task Manager Web Application

## Project Overview
This project is a backend web application built using **Python and SQLite**.  
It implements **CRUD operations (Create, Read, Update, Delete)** for managing tasks through a web interface.

The application runs on a custom HTTP server and dynamically generates HTML pages for the user.

---

## Technologies Used

- Python
- SQLite Database
- HTML
- CSS
- Python HTTPServer

---

## Features

- Add new tasks
- View all tasks
- Edit existing tasks
- Delete tasks
- Dynamic HTML rendering
- Database integration with SQLite
- Input validation and error handling

---

## Database Structure

### Table: tasks

| Column | Type | Description |
|------|------|------|
| id | INTEGER | Primary key with auto increment |
| title | TEXT | Title of the task |
| description | TEXT | Task description |
| status | TEXT | Task status (pending/done) |
| created_at | TEXT | Timestamp when the task was created |

---

## How the System Works

1. The user interacts with the web interface.
2. The browser sends HTTP requests to the Python server.
3. The server processes the request using the TaskHandler class.
4. CRUD operations are performed on the SQLite database.
5. The server generates HTML dynamically and sends it back to the browser.

---

## Running the Application

1. Make sure Python is installed.
2. Run the server:
