data "google_project" "project" {}

resource "google_service_account" "dss-monitor" {
  display_name = "${var.DSS_MON_GCP_SERVICE_ACCOUNT_NAME}"
  account_id = "${var.DSS_MON_GCP_SERVICE_ACCOUNT_NAME}"
}

# Useful command to discover role names (Guessing based on console titles is difficult):
# `gcloud iam list-grantable-roles //cloudresourcemanager.googleapis.com/projects/{project-id}`


resource "google_project_iam_member" "viewer" {
  project = "${data.google_project.project.project_id}"
  role    = "roles/viewer"
  member  = "serviceAccount:${google_service_account.dss-monitor.email}"
}

output "service_account" {
  value = "${var.DSS_MON_GCP_SERVICE_ACCOUNT_NAME}"
}
