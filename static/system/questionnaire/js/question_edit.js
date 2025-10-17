/**
 * 问题编辑页面JavaScript逻辑
 */

// Vue组件和API解构
const { createApp, ref, computed, reactive, onMounted } = Vue;
const {
  NForm,
  NFormItem,
  NInput,
  NSelect,
  NSwitch,
  NInputNumber,
  NButton,
  NIcon,
  NText,
  NCheckbox,
  createDiscreteApi,
} = naive;

// 创建Vue应用
const app = createApp({
  delimiters: ["[[", "]]"],
  setup() {
    // 创建离散API
    const { message, notification, dialog, loadingBar, modal } =
      createDiscreteApi([
        "message",
        "dialog",
        "notification",
        "loadingBar",
        "modal",
      ]);

    // 响应式数据
    const formRef = ref(null);
    const saving = ref(false);

    // 从URL获取问卷ID或问题ID
    const urlPath = window.location.pathname;
    const pathParts = urlPath.split("/");
    const isEditMode = pathParts.includes("edit");
    const questionId = isEditMode ? pathParts[pathParts.length - 1] : null;
    const questionnaireId = isEditMode ? null : pathParts[pathParts.length - 1];

    // 表单数据
    const formData = reactive({
      id: null,
      questionnaireId: questionnaireId,
      title: "",
      description: "",
      questionType: "",
      isRequired: false,
      sortOrder: 0,
      options: [],
    });

    // 问题类型选项
    const questionTypeOptions = [
      { label: "文本输入", value: "text" },
      { label: "多行文本", value: "textarea" },
      { label: "单选题", value: "single_choice" },
      { label: "多选题", value: "multiple_choice" },
      { label: "评分题", value: "rating" },
    ];

    // 表单验证规则
    const rules = {
      title: {
        required: true,
        message: "请输入问题标题",
        trigger: "blur",
      },
      questionType: {
        required: true,
        message: "请选择问题类型",
        trigger: "change",
      },
    };

    // 计算属性：是否显示选项设置
    const showOptions = computed(() => {
      return (
        formData.questionType === "single_choice" ||
        formData.questionType === "multiple_choice" ||
        formData.questionType === "rating"
      );
    });

    // 处理问题类型变化
    const handleQuestionTypeChange = (value) => {
      if (value === "single_choice" || value === "multiple_choice") {
        if (formData.options.length === 0) {
          addOption();
        }
      }
    };

    // 添加选项
    const addOption = () => {
      const newId = Math.max(...formData.options.map((o) => o.id), 0) + 1;
      formData.options.push({
        id: newId,
        text: "",
        value: "",
        isCorrect: false,
        allowInput: false, // 是否允许用户输入自定义内容
      });
    };

    // 删除选项
    const removeOption = (index) => {
      if (formData.options.length > 1) {
        formData.options.splice(index, 1);
      }
    };

    // 保存问题
    const handleSave = async () => {
      try {
        await formRef.value?.validate();
        saving.value = true;

        // 构建保存数据
        const saveData = {
          id: formData.id,
          questionnaire_id: formData.questionnaireId,
          title: formData.title,
          description: formData.description,
          question_type: formData.questionType,
          is_required: formData.isRequired,
          sort_order: formData.sortOrder,
        };

        // 如果是选择题，添加选项数据
        if (showOptions.value) {
          saveData.options = formData.options
            .filter((option) => option.text.trim())
            .map((option) => ({
              text: option.text,
              value: option.value || option.text,
              is_correct: option.isCorrect,
              allow_input: option.allowInput, // 是否允许用户输入
            }));
        }

        console.log("保存数据:", saveData);

        // 调用API保存数据
        let response;
        if (saveData.id) {
          // 更新问题
          response = await fetch("/system/questionnaire/question/update", {
            method: "PUT",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(saveData),
          });
        } else {
          // 新增问题
          response = await fetch("/system/questionnaire/question/save", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(saveData),
          });
        }

        const result = await response.json();
        if (result.success) {
          message.success(result.msg || "保存成功！");
          setTimeout(() => {
            if (window.parent && window.parent.layer) {
              // 获取当前layer的索引并只关闭当前layer
              const index = window.parent.layer.getFrameIndex(window.name);
              window.parent.layer.close(index);
              // 重新加载父级layer的数据而不是整个页面
              if (window.parent.loadQuestionList) {
                window.parent.loadQuestionList();
              }
            }
          }, 1000);
        } else {
          message.error(result.msg || "保存失败！");
        }
      } catch (error) {
        console.error("验证失败:", error);
        message.error("请检查表单数据");
      } finally {
        saving.value = false;
      }
    };

    // 取消操作
    const handleCancel = () => {
      if (window.parent && window.parent.layer) {
        // 获取当前layer的索引并只关闭当前layer
        const index = window.parent.layer.getFrameIndex(window.name);
        window.parent.layer.close(index);
      }
    };

    // 加载问题详情（编辑模式）
    const loadQuestionDetail = async () => {
      if (!questionId) return;

      try {
        const response = await fetch(
          `/system/questionnaire/question/detail/${questionId}`
        );
        const result = await response.json();

        if (result.success && result.data) {
          const data = result.data;

          // 回填表单数据
          formData.id = data.id;
          formData.questionnaireId = data.questionnaire_id;
          formData.title = data.title;
          formData.description = data.description || "";
          formData.questionType = data.question_type;
          formData.isRequired = data.is_required;
          formData.sortOrder = data.sort_order;

          // 回填选项数据
          if (data.options && data.options.length > 0) {
            formData.options = data.options.map((option, index) => ({
              id: option.id || index + 1,
              text: option.text,
              value: option.value,
              isCorrect: option.is_correct || false,
              allowInput: option.allow_input || false, // 是否允许用户输入
            }));
          } else {
            formData.options = [];
          }
        } else {
          message.error(result.msg || "加载问题详情失败");
        }
      } catch (error) {
        console.error("加载问题详情失败:", error);
        message.error("加载问题详情失败");
      }
    };

    // 页面初始化
    onMounted(() => {
      if (isEditMode) {
        loadQuestionDetail();
      }
    });

    // 返回组件数据和方法
    return {
      formRef,
      formData,
      rules,
      questionTypeOptions,
      showOptions,
      saving,
      handleQuestionTypeChange,
      addOption,
      removeOption,
      handleSave,
      handleCancel,
    };
  },
});

// 使用Naive UI并挂载应用
app.use(naive);
app.mount("#app");