# import datetime

from datetime import datetime


string = "2019-11-20T10:00:28.584127Z"
string = string.replace("T", " ").replace("Z", "")

print(string)

now = datetime.fromisoformat(string)

# get current date
# now = datetime.now()


# convert current date into timestamp
timestamp = datetime.timestamp(now)

print("Date and Time :", now)
print("Timestamp:", timestamp)

print("asdasdf.645645645".strip("."))
