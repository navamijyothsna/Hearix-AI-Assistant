const API_URL = 'http://127.0.0.1:8000';

// Detect Current Page
const isLoginPage = window.location.pathname.endsWith('index.html') || window.location.pathname.endsWith('admin/');
const token = localStorage.getItem('admin_token');

if (isLoginPage && token) {
    window.location.href = 'dashboard.html';
} else if (!isLoginPage && !token) {
    window.location.href = 'index.html';
}

// Login Logic
const loginForm = document.getElementById('login-form');
if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const errorMsg = document.getElementById('error-msg');

        try {
            const formData = new URLSearchParams();
            formData.append('username', username);
            formData.append('password', password);

            const response = await fetch(`${API_URL}/admin/token`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                localStorage.setItem('admin_token', data.access_token);
                window.location.href = 'dashboard.html';
            } else {
                errorMsg.innerText = "Invalid credentials";
            }
        } catch (error) {
            errorMsg.innerText = "Server error";
        }
    });
}

// Dashboard Logic
if (!isLoginPage) {
    document.getElementById('logout-btn').addEventListener('click', () => {
        localStorage.removeItem('admin_token');
        window.location.href = 'index.html';
    });

    // Fetch and render syllabus
    async function loadSyllabus() {
        try {
            const response = await fetch(`${API_URL}/admin/syllabus`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.status === 401) {
                localStorage.removeItem('admin_token');
                window.location.href = 'index.html';
                return;
            }

            const syllabus = await response.json();
            renderSyllabus(syllabus);
            updateDropdowns(syllabus);
        } catch (e) {
            console.error(e);
            document.getElementById('syllabus-content').innerText = "Failed to load syllabus.";
        }
    }

    function renderSyllabus(syllabus) {
        const container = document.getElementById('syllabus-content');
        container.innerHTML = '';

        if (syllabus.length === 0) {
            container.innerHTML = '<p>No folders created yet.</p>';
            return;
        }

        const ul = document.createElement('ul');
        ul.className = 'syllabus-tree';

        syllabus.forEach(sem => {
            const liSem = document.createElement('li');
            liSem.innerHTML = `<strong>📁 ${sem.name}</strong>`;

            if (sem.subjects && sem.subjects.length > 0) {
                const ulSubj = document.createElement('ul');
                ulSubj.className = 'syllabus-tree';
                sem.subjects.forEach(subj => {
                    const liSubj = document.createElement('li');
                    liSubj.innerHTML = `<strong>📁 ${subj.name}</strong>`;

                    if (subj.modules && subj.modules.length > 0) {
                        const ulMod = document.createElement('ul');
                        ulMod.className = 'syllabus-tree';
                        subj.modules.forEach(mod => {
                            const liMod = document.createElement('li');
                            liMod.innerHTML = `<strong>📁 ${mod.name}</strong>`;

                            if (mod.files && mod.files.length > 0) {
                                const ulFile = document.createElement('ul');
                                ulFile.className = 'syllabus-tree';
                                mod.files.forEach(f => {
                                    const liFile = document.createElement('li');
                                    liFile.innerHTML = `📄 ${f}`;
                                    liFile.style.color = 'var(--text-secondary)';
                                    ulFile.appendChild(liFile);
                                });
                                liMod.appendChild(ulFile);
                            }
                            ulMod.appendChild(liMod);
                        });
                        liSubj.appendChild(ulMod);
                    }
                    ulSubj.appendChild(liSubj);
                });
                liSem.appendChild(ulSubj);
            }
            ul.appendChild(liSem);
        });

        container.appendChild(ul);
    }

    function updateDropdowns(syllabus) {
        const parentPath = document.getElementById('parent-path');
        const uploadPath = document.getElementById('upload-path');

        parentPath.innerHTML = '<option value="">Root (Create Semester)</option>';
        uploadPath.innerHTML = '<option value="">Select Target Path (Semester/Subject/Module)</option>';

        syllabus.forEach(sem => {
            parentPath.innerHTML += `<option value="${sem.name}">${sem.name} (Create Subject)</option>`;
            // We can also upload directly to a semester if we want, but usually to module
            uploadPath.innerHTML += `<option value="${sem.name}">${sem.name}</option>`;

            if (sem.subjects) {
                sem.subjects.forEach(subj => {
                    const subjPath = `${sem.name}/${subj.name}`;
                    parentPath.innerHTML += `<option value="${subjPath}">&nbsp;&nbsp;↳ ${subjPath} (Create Module)</option>`;
                    uploadPath.innerHTML += `<option value="${subjPath}">&nbsp;&nbsp;↳ ${subjPath}</option>`;

                    if (subj.modules) {
                        subj.modules.forEach(mod => {
                            const modPath = `${subjPath}/${mod.name}`;
                            // Cannot nest deeper than Module for syllabus creation in the UI
                            uploadPath.innerHTML += `<option value="${modPath}">&nbsp;&nbsp;&nbsp;&nbsp;↳ ${modPath}</option>`;
                        });
                    }
                });
            }
        });
    }

    // Create Folder
    document.getElementById('create-folder-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const parent_path = document.getElementById('parent-path').value;
        const name = document.getElementById('folder-name').value;
        const status = document.getElementById('create-status');

        try {
            const res = await fetch(`${API_URL}/admin/folder`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ name, parent_path })
            });
            if (res.ok) {
                status.style.color = '#10b981';
                status.innerText = "Folder created successfully!";
                document.getElementById('folder-name').value = '';
                loadSyllabus();
            } else {
                status.style.color = '#ef4444';
                status.innerText = "Failed to create folder.";
            }
        } catch (err) {
            status.innerText = "Error creating folder.";
        }
        setTimeout(() => status.innerText = "", 3000);
    });

    // Upload File
    document.getElementById('upload-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const path = document.getElementById('upload-path').value;
        const fileInput = document.getElementById('pdf-file');
        const status = document.getElementById('upload-status');

        if (!path) {
            status.style.color = '#ef4444';
            status.innerText = "Please select a target path.";
            return;
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('path', path);

        status.style.color = 'var(--text-primary)';
        status.innerText = "Uploading...";

        try {
            const res = await fetch(`${API_URL}/admin/upload`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData
            });
            if (res.ok) {
                status.style.color = '#10b981';
                status.innerText = "Upload successful!";
                fileInput.value = '';
                loadSyllabus();
            } else {
                status.style.color = '#ef4444';
                status.innerText = "Upload failed.";
            }
        } catch (err) {
            status.style.color = '#ef4444';
            status.innerText = "Error uploading file.";
        }
        setTimeout(() => status.innerText = "", 3000);
    });

    loadSyllabus();
}
