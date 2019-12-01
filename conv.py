class a:
    def __init__(self):
        self.value_a = 10

class b:
    def __init__(self, value_a, obj_a):
        self.value_b = value_a
        self.obj_a = obj_a

a_instance = a()
b_instance = b(a_instance.value_a, a_instance)

print(b_instance.value_b)
a_instance.value_a = 20
print(b_instance.value_b)

print(b_instance.obj_a.value_a)
