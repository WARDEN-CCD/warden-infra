# Cost guardrail (ADR-004): alerts at 25/50/75 % of the yearly student credit.

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "5.10.0"
    }
  }
}

variable "subscription_id" {
  type = string
}

variable "amount_usd" {
  type    = number
  default = 100
}

variable "start_date" {
  type        = string
  description = "First day of the current month, RFC 3339 (e.g. 2026-10-01T00:00:00Z)."
}

variable "contact_emails" {
  type = list(string)
}

resource "azurerm_consumption_budget_subscription" "warden" {
  name            = "warden-student-credit"
  subscription_id = "/subscriptions/${var.subscription_id}"
  amount          = var.amount_usd
  time_grain      = "Annually"

  time_period {
    start_date = var.start_date
  }

  dynamic "notification" {
    for_each = [25, 50, 75]
    content {
      enabled        = true
      threshold      = notification.value
      operator       = "GreaterThan"
      threshold_type = "Actual"
      contact_emails = var.contact_emails
    }
  }
}
