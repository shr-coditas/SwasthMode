"""Local developer commands; never exposed as public API operations."""
import argparse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from app.core.db import model_registry  # noqa: F401
from app.core.db.session import sessions
from app.features.account.setup import assign, map_account
from app.features.patients.models import Patient
from app.features.patients.seed import seed


def main():
    parser = argparse.ArgumentParser(prog="uv run python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("seed")
    commands.add_parser("patients")
    patient = commands.add_parser("map-patient")
    patient.add_argument("--user-id", required=True)
    patient.add_argument("--patient-id", required=True)
    clinician = commands.add_parser("map-clinician")
    clinician.add_argument("--user-id", required=True)
    assignment = commands.add_parser("assign")
    assignment.add_argument("--clinician-id", required=True)
    assignment.add_argument("--patient-id", required=True)
    args = parser.parse_args()
    try:
        if args.command == "seed":
            print(seed())
        elif args.command == "patients":
            with sessions()() as db:
                for row in db.scalars(select(Patient).order_by(Patient.name)):
                    print(f"{row.id}  {row.name}  {row.timezone}")
        elif args.command == "map-patient":
            map_account(args.user_id, "patient", args.patient_id)
            print("Patient mapping saved")
        elif args.command == "map-clinician":
            map_account(args.user_id, "clinician", None)
            print("Clinician mapping saved")
        elif args.command == "assign":
            assign(args.clinician_id, args.patient_id)
            print("Assignment saved")
    except ValueError as error:
        parser.exit(2, str(error) + "\n")
    except SQLAlchemyError:
        parser.exit(2, "Database operation failed. Check local configuration and migrations.\n")


if __name__ == "__main__":
    main()
