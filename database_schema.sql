CREATE DATABASE IF NOT EXISTS food_donation_system;
USE food_donation_system;

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    mobile VARCHAR(15) NOT NULL,
    password VARCHAR(255) NOT NULL,
    user_type ENUM('donor', 'ngo', 'volunteer') NOT NULL,
    is_blocked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Donations Table
CREATE TABLE IF NOT EXISTS donations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    donor_id INT,
    food_type VARCHAR(100) NOT NULL,
    quantity VARCHAR(50) NOT NULL,
    expiration_date DATE NOT NULL,
    food_condition TEXT,
    pickup_location TEXT NOT NULL,
    food_image VARCHAR(255),
    status ENUM('pending', 'accepted', 'in_transit', 'delivered', 'completed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (donor_id) REFERENCES users(id)
);

-- Donation Requests Table
CREATE TABLE IF NOT EXISTS donation_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    donation_id INT,
    ngo_id INT,
    volunteer_id INT NOT NULL,
    ngo_address TEXT NOT NULL,
    reason TEXT NOT NULL,
    status ENUM('pending', 'accepted', 'rejected', 'picked_up', 'completed') DEFAULT 'pending',
    feedback_given BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rejection_reason TEXT,
    rejection_images TEXT,
    rejected_at TIMESTAMP NULL,
    rejected_by INT,
    FOREIGN KEY (donation_id) REFERENCES donations(id),
    FOREIGN KEY (ngo_id) REFERENCES users(id),
    FOREIGN KEY (volunteer_id) REFERENCES users(id),
    FOREIGN KEY (rejected_by) REFERENCES users(id)
);

-- Admin Table
CREATE TABLE IF NOT EXISTS admin (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    password VARCHAR(255) NOT NULL,
    secret_key VARCHAR(100) NOT NULL
);

-- Feedback Table
CREATE TABLE IF NOT EXISTS feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    donation_request_id INT NOT NULL,
    ngo_id INT NOT NULL,
    donor_id INT NOT NULL,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (donation_request_id) REFERENCES donation_requests(id),
    FOREIGN KEY (ngo_id) REFERENCES users(id),
    FOREIGN KEY (donor_id) REFERENCES users(id)
);

-- Default Admin User
INSERT IGNORE INTO admin (username, password, secret_key) 
VALUES ('admin', 'admin123', 'secretkey123');

-- Indexes for Better Performance
CREATE INDEX IF NOT EXISTS idx_donor_id ON donations(donor_id);
CREATE INDEX IF NOT EXISTS idx_ngo_id ON donation_requests(ngo_id);
CREATE INDEX IF NOT EXISTS idx_volunteer_id ON donation_requests(volunteer_id);

DESCRIBE donation_requests;