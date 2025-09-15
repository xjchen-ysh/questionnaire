/**
 * 问卷设计页面JavaScript逻辑
 */

// Vue组件和API解构
const { createApp, ref, reactive, computed, onMounted } = Vue;
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
  NCard,
  NSpace,
  NCheckbox,
  NRadio,
  NRadioGroup,
  NCheckboxGroup,
  NRate,
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
    const publishing = ref(false);
    const questionnaire = ref({});
    const questions = ref([]);

    // 从URL获取问卷ID
    const urlPath = window.location.pathname;
    const pathParts = urlPath.split("/");
    const questionnaireId = pathParts[pathParts.length - 1];

    // 新问题表单数据
    const newQuestion = reactive({
      title: "",
      description: "",
      questionType: "",
      isRequired: false,
      sortOrder: 0,
      options: [],
    });

    // 问题类型配置
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
        newQuestion.questionType === "single_choice" ||
        newQuestion.questionType === "multiple_choice"
      );
    });

    // 获取问题类型显示名称
    const getQuestionTypeLabel = (type) => {
      const option = questionTypeOptions.find((opt) => opt.value === type);
      return option ? option.label : type;
    };

    // 处理问题类型变化
    const handleQuestionTypeChange = (value) => {
      if (value === "single_choice" || value === "multiple_choice") {
        if (newQuestion.options.length === 0) {
          addOption();
        }
      }
    };

    // 添加选项
    const addOption = () => {
      const newId = Math.max(...newQuestion.options.map((o) => o.id), 0) + 1;
      newQuestion.options.push({
        id: newId,
        text: "",
        value: "",
        isCorrect: false,
      });
    };

    // 删除选项
    const removeOption = (index) => {
      if (newQuestion.options.length > 1) {
        newQuestion.options.splice(index, 1);
      }
    };

    // 添加问题
    const addQuestion = async () => {
      try {
        await formRef.value?.validate();
        saving.value = true;

        // 构建保存数据
        const saveData = {
          questionnaire_id: questionnaireId,
          title: newQuestion.title,
          description: newQuestion.description,
          question_type: newQuestion.questionType,
          is_required: newQuestion.isRequired,
          sort_order: newQuestion.sortOrder || questions.value.length + 1,
        };

        // 如果是选择题，添加选项数据
        if (showOptions.value) {
          saveData.options = newQuestion.options
            .filter((option) => option.text.trim())
            .map((option) => ({
              text: option.text,
              value: option.value || option.text,
              is_correct: option.isCorrect,
            }));
        }

        console.log("保存数据:", saveData);

        // 调用API保存数据
        const response = await fetch("/system/questionnaire/question/save", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(saveData),
        });

        const result = await response.json();
        if (result.success) {
          message.success(result.msg || "添加问题成功！");
          // 重置表单
          resetForm();
          // 重新加载问题列表
          loadQuestions();
        } else {
          message.error(result.msg || "添加问题失败！");
        }
      } catch (error) {
        console.error("验证失败:", error);
        message.error("请检查表单数据");
      } finally {
        saving.value = false;
      }
    };

    // 重置表单
    const resetForm = () => {
      newQuestion.title = "";
      newQuestion.description = "";
      newQuestion.questionType = "";
      newQuestion.isRequired = false;
      newQuestion.sortOrder = 0;
      newQuestion.options = [];
    };

    // 编辑问题
    const editQuestion = (question) => {
      const url = `/system/questionnaire/question/edit/${question.id}`;
      layer.open({
        type: 2,
        title: "编辑问题",
        content: url,
        area: ["800px", "600px"],
        maxmin: true,
        end: function () {
          loadQuestions();
        },
      });
    };

    // 删除问题
    const deleteQuestion = (question) => {
      dialog.warning({
        title: "确认删除",
        content: `确定要删除问题"${question.title}"吗？`,
        positiveText: "确定",
        negativeText: "取消",
        onPositiveClick: async () => {
          try {
            const response = await fetch(
              `/system/questionnaire/question/delete/${question.id}`,
              {
                method: "DELETE",
              }
            );
            const result = await response.json();
            if (result.success) {
              message.success(result.msg || "删除成功！");
              loadQuestions();
            } else {
              message.error(result.msg || "删除失败！");
            }
          } catch (error) {
            console.error("删除失败:", error);
            message.error("删除失败！");
          }
        },
      });
    };

    // 预览问卷
    const previewQuestionnaire = () => {
      const url = `/system/questionnaire/preview/${questionnaireId}`;
      window.open(url, "_blank");
    };

    // 发布问卷
    const publishQuestionnaire = async () => {
      if (questions.value.length === 0) {
        message.warning("请先添加问题后再发布！");
        return;
      }

      dialog.info({
        title: "确认发布",
        content: "确定要发布这份问卷吗？发布后将可以开始收集回答。",
        positiveText: "确定发布",
        negativeText: "取消",
        onPositiveClick: async () => {
          try {
            publishing.value = true;
            const response = await fetch(
              `/system/questionnaire/publish/${questionnaireId}`,
              {
                method: "POST",
              }
            );
            const result = await response.json();
            if (result.success) {
              message.success(result.msg || "发布成功！");
              loadQuestionnaireInfo();
            } else {
              message.error(result.msg || "发布失败！");
            }
          } catch (error) {
            console.error("发布失败:", error);
            message.error("发布失败！");
          } finally {
            publishing.value = false;
          }
        },
      });
    };

    // 加载问题列表
    const loadQuestions = async () => {
      try {
        const response = await fetch(
          `/system/questionnaire/questions/${questionnaireId}`
        );
        const result = await response.json();
        if (result.success) {
          questions.value = result.data || [];
        } else {
          message.error(result.msg || "加载问题列表失败");
        }
      } catch (error) {
        console.error("加载问题列表失败:", error);
        message.error("加载问题列表失败");
      }
    };

    // 加载问卷信息
    const loadQuestionnaireInfo = async () => {
      try {
        const response = await fetch(
          `/system/questionnaire/detail/${questionnaireId}`
        );
        const result = await response.json();
        if (result.success) {
          questionnaire.value = result.data || {};
        } else {
          message.error(result.msg || "加载问卷信息失败");
        }
      } catch (error) {
        console.error("加载问卷信息失败:", error);
        message.error("加载问卷信息失败");
      }
    };

    // 页面初始化
    onMounted(() => {
      loadQuestionnaireInfo();
      loadQuestions();
    });

    // 返回组件数据和方法
    return {
      formRef,
      newQuestion,
      rules,
      questionTypeOptions,
      showOptions,
      saving,
      publishing,
      questionnaire,
      questions,
      getQuestionTypeLabel,
      handleQuestionTypeChange,
      addOption,
      removeOption,
      addQuestion,
      editQuestion,
      deleteQuestion,
      previewQuestionnaire,
      publishQuestionnaire,
    };
  },
});

// 使用Naive UI并挂载应用
app.use(naive);
app.mount("#app");