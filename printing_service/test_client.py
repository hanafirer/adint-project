from xmlrpc import client

proxy = client.ServerProxy("http://localhost:5003/api")

print(proxy.print_sheets(1, "Mathematics", "2026-11-20 09:00", 5))
print(proxy.print_sheets(1, "Mathematics", "2026-11-20 09:00", 5))   # mora reči "already printed"
print(proxy.print_sheets(2, "Physics", "2026-11-22 14:00", 3))