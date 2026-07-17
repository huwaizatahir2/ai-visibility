data "aws_availability_zones" "available" {
  state = "available"
}

# Latest Ubuntu 24.04 LTS AMI (Canonical).
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
}

# ---------------------------------------------------------------------------
# Network: one VPC, one public subnet (app host) + two private subnets (RDS).
# ---------------------------------------------------------------------------
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "${var.name}-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${var.name}-igw" }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, 0)
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.name}-public" }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  tags              = { Name = "${var.name}-private-${count.index}" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "${var.name}-public-rt" }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# ---------------------------------------------------------------------------
# Security groups
# ---------------------------------------------------------------------------
resource "aws_security_group" "app" {
  name        = "${var.name}-app"
  description = "App host: web from anywhere, SSH from admin only"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH from admin CIDR"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.name}-app-sg" }
}

resource "aws_security_group" "db" {
  name        = "${var.name}-db"
  description = "PostgreSQL from the app host only"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from app"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.name}-db-sg" }
}

# ---------------------------------------------------------------------------
# App host + Elastic IP
# ---------------------------------------------------------------------------
resource "aws_instance" "app" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.app.id]
  key_name               = var.key_pair_name

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
    encrypted   = true
  }

  tags = { Name = "${var.name}-app" }
}

resource "aws_eip" "app" {
  instance = aws_instance.app.id
  domain   = "vpc"
  tags     = { Name = "${var.name}-eip" }
}

# ---------------------------------------------------------------------------
# RDS PostgreSQL (private) + generated master password in SSM.
# ---------------------------------------------------------------------------
resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_ssm_parameter" "db_password" {
  name  = "/${var.name}/db_password"
  type  = "SecureString"
  value = random_password.db.result
}

resource "aws_db_subnet_group" "main" {
  name       = "${var.name}-db-subnets"
  subnet_ids = aws_subnet.private[*].id
  tags       = { Name = "${var.name}-db-subnets" }
}

resource "aws_db_instance" "main" {
  identifier              = "${var.name}-db"
  engine                  = "postgres"
  engine_version          = "18"
  instance_class          = var.db_instance_class
  allocated_storage       = var.db_allocated_storage
  storage_encrypted       = true
  db_name                 = var.db_name
  username                = var.db_username
  password                = random_password.db.result
  db_subnet_group_name    = aws_db_subnet_group.main.name
  vpc_security_group_ids  = [aws_security_group.db.id]
  backup_retention_period = var.backup_retention_days
  skip_final_snapshot     = false
  final_snapshot_identifier = "${var.name}-db-final"
  deletion_protection     = true
  multi_az                = false
  tags                    = { Name = "${var.name}-db" }
}
