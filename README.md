# QueryOS

A Flask-based web application for managing production and cutting data.

## Features

- Dashboard with overview of different data tables
- Production Data management
- Cutting Data management
- Tab Production Data management
- Search and filter functionality
- Pagination support
- Responsive design

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/QueryOS.git
cd QueryOS
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory with the following variables:
```
SECRET_KEY=your_secret_key
DB_HOST=localhost
DB_NAME=your_database
DB_USER=your_username
DB_PASSWORD=your_password
```

## Running the Application

1. Start the development server:
```bash
python run.py
```

2. Access the application at `http://localhost:5000`

## Project Structure

```
QueryOS/
├── app/
│   ├── routes/         # Route handlers
│   ├── models/         # Database models
│   └── __init__.py     # Application factory
├── static/             # Static files (CSS, JS)
├── templates/          # HTML templates
├── tests/             # Test files
├── .env               # Environment variables
├── requirements.txt   # Project dependencies
└── run.py            # Application entry point
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
