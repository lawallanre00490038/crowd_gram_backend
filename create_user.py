import pandas as pd

# Data for users
data = [
    {"name": "Jane Doe", "email": "jane@example.com", "password": "pass123", "role": "agent", "language": "English, Yoruba", "dialect": "Ekiti, Ibadan", "telegram_id": "@janedoe"},
    {"name": "John Smith", "email": "john@example.com", "password": "secret456", "role": "agent", "language": "English", "dialect": "Lagos", "telegram_id": "@johnsmith"},
    {"name": "Mary Johnson", "email": "mary@example.com", "password": "mypass789", "role": "admin", "language": "Yoruba, Hausa", "dialect": "Oyo, Kano", "telegram_id": "@maryj"},
    {"name": "Peter Okoro", "email": "peter@example.com", "password": "peter321", "role": "agent", "language": "English, Igbo", "dialect": "Enugu, Owerri", "telegram_id": "@peterokoro"},
    {"name": "Aisha Bello", "email": "aisha@example.com", "password": "aisha111", "role": "agent", "language": "Hausa, English", "dialect": "Kaduna, Sokoto", "telegram_id": "@aishab"},
]

# Create DataFrame
df = pd.DataFrame(data)

# Save as Excel
df.to_excel("users_sample.xlsx", index=False)
print("Excel file 'users_sample.xlsx' created successfully!")
