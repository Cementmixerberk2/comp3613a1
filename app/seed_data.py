SEED_USERS = [
    ("admin", "admin@northwindstudio.com", "adminpass", "admin"),
    ("northwind", "hello@northwindstudio.com", "companypass", "company"),
    ("company1", "company1@northwindstudio.com", "companypass", "company"),
    ("ava_thompson", "ava.thompson@example.com", "studentpass", "student"),
    ("student1", "student1@example.com", "studentpass", "student"),
    ("leo_martinez", "leo.martinez@example.com", "studentpass", "student"),
    ("mia_ross", "mia.ross@example.com", "studentpass", "student"),
    ("noah_chen", "noah.chen@example.com", "studentpass", "student"),
    ("sophia_nguyen", "sophia.nguyen@example.com", "studentpass", "student"),
]

SEED_STUDENTS = {
    "ava_thompson": {"full_name": "Ava Thompson", "major": "Computer Science", "gpa": 3.91},
    "student1": {"full_name": "Student One", "major": "Undecided", "gpa": 0.00},
    "leo_martinez": {"full_name": "Leo Martinez", "major": "Software Engineering", "gpa": 3.76},
    "mia_ross": {"full_name": "Mia Ross", "major": "Business Analytics", "gpa": 3.83},
    "noah_chen": {"full_name": "Noah Chen", "major": "Data Science", "gpa": 3.69},
    "sophia_nguyen": {"full_name": "Sophia Nguyen", "major": "UX Design", "gpa": 3.88},
}

SEED_POSITIONS = [
    ("Software Engineering Intern", "Build production-ready features and work closely with the engineering team.", 3),
    ("Product Design Intern", "Design polished user experiences and help shape new product flows.", 2),
    ("Data Analytics Intern", "Analyze hiring, engagement, and product usage trends to guide decisions.", 2),
    ("Marketing Intern", "Support campaigns, storytelling, and internship promotion across channels.", 1),
]

SEED_APPLICATIONS = [
    ("ava_thompson", "Product Design Intern", "I’m a Computer Science student with a strong interest in user-centered design and rapid prototyping."),
    ("ava_thompson", "Software Engineering Intern", "I enjoy building thoughtful backend features and would love to contribute to a product team."),
    ("leo_martinez", "Software Engineering Intern", "I’ve built Python and JavaScript projects for coursework and want to deepen my engineering skills."),
    ("leo_martinez", "Product Design Intern", "I enjoy translating technical ideas into clean, intuitive user experiences and product flows."),
    ("mia_ross", "Data Analytics Intern", "I’m excited to work with data storytelling and help turn trends into actionable recommendations."),
    ("mia_ross", "Marketing Intern", "I love campaign planning and connecting student audiences to opportunities in a compelling way."),
    ("noah_chen", "Data Analytics Intern", "I want to build reporting dashboards and help the team measure what matters most."),
    ("noah_chen", "Marketing Intern", "I have a strong interest in data-driven marketing and stakeholder communication."),
    ("sophia_nguyen", "Product Design Intern", "I enjoy designing interfaces that balance usability, accessibility, and business goals."),
    ("sophia_nguyen", "Marketing Intern", "I’m eager to contribute to creative campaigns and help shape the brand story."),
]
