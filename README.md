# certificate-service

This project is a FastAPI application that generates certificates based on data received from a Next.js application. It utilizes a PowerPoint template for certificate generation and returns the generated PDF certificate for download or display.

## Project Structure

```
certificate-service
├── src
│   ├── api
│   │   ├── endpoints
│   │   │   └── certificates.py  # FastAPI endpoints for certificate generation
│   │   └── deps.py               # Dependency functions for API endpoints
│   ├── core
│   │   ├── config.py              # Application configuration settings
│   │   └── security.py            # Security-related functions
│   ├── models
│   │   └── certificate.py          # Data models for certificate generation
│   ├── services
│   │   └── certificate_generator.py # Logic for generating certificates
│   ├── templates
│   │   └── certificate_template.pptx # PowerPoint template for certificates
│   └── main.py                    # Entry point of the FastAPI application
├── tests
│   ├── api
│   │   └── test_certificates.py    # Unit tests for API endpoints
│   └── conftest.py                 # Test configuration and fixtures
├── .env                             # Environment variables
├── .gitignore                       # Files and directories to ignore by Git
├── requirements.txt                 # Python dependencies
└── README.md                        # Project documentation
```

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd certificate-service
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   uvicorn src.main:app --reload
   ```

5. **Access the API:**
   The API will be available at `http://localhost:8000`. You can use tools like Postman or cURL to send requests to the endpoints.

## Usage

Send a POST request to the `/` endpoint with the required data to generate a certificate. The response will include the generated PDF certificate.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.