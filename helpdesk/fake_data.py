import random

from .models import User, Ticket, TicketComment, TicketProblemCategory


def maybe_true(l=0.5):
    return random.random() >= 0.5


def create_fake_data():
    print("Creating super admin")
    superadmin = User.objects.create_superuser(username="superadmin", email="superadmin@test.com", password="test", displayed_name="Super Admin")

    print("Creating agent1")
    agent1 = User.objects.create_customer_support_agent(username="agent1", email="agent1@test.com", password="test", displayed_name="Agent1")

    print("Creating agent2")
    agent2 = User.objects.create_customer_support_agent(username="agent2", email="agent2@test.com", password="test", displayed_name="Agent2")

    print("Creating agent3")
    agent3 = User.objects.create_customer_support_agent(username="agent3", email="agent3@test.com", password="test", displayed_name="Agent3")

    print("Creating agent4")
    agent4 = User.objects.create_customer_support_agent(username="agent4", email="agent4@test.com", password="test", displayed_name="Agent4")

    print("Creating agent5")
    agent5 = User.objects.create_customer_support_agent(username="agent5", email="agent5@test.com", password="test", displayed_name="Agent5")

#    agent_role = RoleModel.objects.create(name="agent")
#    agent1.roles.add(agent_role)

    print("Creating customer1")
    customer1 = User.objects.create_customer(username="customer1", email="test@test.com", password="test", displayed_name="Customer Test1")

    print("Creating customer2")
    customer2 = User.objects.create_customer(username="customer2", email="test2@test.com", password="test", displayed_name="Customer Test2")

    print("Creating customer3")
    customer3 = User.objects.create_customer(username="customer3", email="test3@test.com", password="test", displayed_name="Customer Test3")

    print("Creating customer4")
    customer4 = User.objects.create_customer(username="customer4", email="test4@test.com", password="test", displayed_name="Customer Test4")

    print("Creating customer5")
    customer5 = User.objects.create_customer(username="customer5", email="test5@test.com", password="test", displayed_name="Customer Test5")

    print("Creating customer6")
    customer6 = User.objects.create_customer(username="customer6", email="test6@test.com", password="test", displayed_name="Customer Test6")

    print("Creating customer7")
    customer7 = User.objects.create_customer(username="customer7", email="test7@test.com", password="test", displayed_name="Customer Test7")

    print("Creating customer8")
    customer8 = User.objects.create_customer(username="customer8", email="test8@test.com", password="test", displayed_name="Customer Test8")

    print("Creating customer9")
    customer9 = User.objects.create_customer(username="customer9", email="test9@test.com", password="test", displayed_name="Customer Test9")

    print("Creating customer10")
    customer10 = User.objects.create_customer(username="customer10", email="test10@test.com", password="test", displayed_name="Customer Test10")


    ticket_problem_category1 = TicketProblemCategory.objects.create(name='Instalación de wordpress')
    ticket_problem_category2 = TicketProblemCategory.objects.create(name='Plugin de wordpress')
    ticket_problem_category3 = TicketProblemCategory.objects.create(name='Tema de wordpress')
    ticket_problem_category4 = TicketProblemCategory.objects.create(name='Woocommerce')
    ticket_problem_category4 = TicketProblemCategory.objects.create(name='Visual composer')
    ticket_problem_category5 = TicketProblemCategory.objects.create(name='Elementor')
    ticket_problem_category6 = TicketProblemCategory.objects.create(name='Dominio')
    ticket_problem_category7 = TicketProblemCategory.objects.create(name='Email')

    print("Creating ticket for customer 1 'El servidor está caido'")
    ticket1 = Ticket.objects.create(customer=customer1, problem_category=ticket_problem_category1, subject="El servidor está caido")

    comment11 = TicketComment.objects.create(ticket=ticket1, text="He intentando entrar a la página esta tarde pero no había forma de entrar")
    comment12 = TicketComment.objects.create(ticket=ticket1, text="¿Cual es el nombre de la instalación?", customer_support_agent=agent1)

    comment13 = TicketComment.objects.create(ticket=ticket1, text="Se llama test1")

    for i in range(30):            
        text = "bla bla bla " * random.randrange(1, 30)

        if maybe_true():
            TicketComment.objects.create(ticket=ticket1, text=text, read=False, customer_support_agent=agent1)
        else:
            TicketComment.objects.create(ticket=ticket1, text=text)

