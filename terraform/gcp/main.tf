terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# VPC Network
resource "google_compute_network" "mantrix_vpc" {
  name                    = "${var.project_name}-vpc"
  auto_create_subnetworks = false
}

# Subnet
resource "google_compute_subnetwork" "mantrix_subnet" {
  name          = "${var.project_name}-subnet"
  ip_cidr_range = "10.0.1.0/24"
  region        = var.region
  network       = google_compute_network.mantrix_vpc.id
}

# Firewall Rules
resource "google_compute_firewall" "allow_ssh" {
  name    = "${var.project_name}-allow-ssh"
  network = google_compute_network.mantrix_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["${var.project_name}-vm"]
}

resource "google_compute_firewall" "allow_http" {
  name    = "${var.project_name}-allow-http"
  network = google_compute_network.mantrix_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["80"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["${var.project_name}-vm"]
}

resource "google_compute_firewall" "allow_https" {
  name    = "${var.project_name}-allow-https"
  network = google_compute_network.mantrix_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["${var.project_name}-vm"]
}

# Firewall for application ports
resource "google_compute_firewall" "allow_app_ports" {
  name    = "${var.project_name}-allow-app-ports"
  network = google_compute_network.mantrix_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["3000", "5001"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["${var.project_name}-vm"]
}

# Static IP Address
resource "google_compute_address" "mantrix_ip" {
  name = "${var.project_name}-static-ip"
}

# Compute Instance (e2-medium: 2 vCPU, 4GB RAM ~= t3.medium)
resource "google_compute_instance" "mantrix_vm" {
  name         = "${var.project_name}-vm"
  machine_type = var.machine_type
  zone         = var.zone

  tags = ["${var.project_name}-vm", "http-server", "https-server"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = var.disk_size_gb
      type  = "pd-standard"
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.mantrix_subnet.id

    access_config {
      nat_ip = google_compute_address.mantrix_ip.address
    }
  }

  metadata = {
    ssh-keys = "${var.ssh_user}:${file(var.ssh_public_key_path)}"
  }

  metadata_startup_script = file("${path.module}/startup-script.sh")

  service_account {
    scopes = ["cloud-platform"]
  }

  labels = {
    environment = "production"
    application = "mantrix-madison"
    project     = var.project_name
  }
}

# DNS Record (if using Cloud DNS)
resource "google_dns_record_set" "mantrix_a" {
  count = var.use_cloud_dns ? 1 : 0

  name         = "${var.domain_name}."
  type         = "A"
  ttl          = 300
  managed_zone = var.dns_zone_name
  rrdatas      = [google_compute_address.mantrix_ip.address]
}
